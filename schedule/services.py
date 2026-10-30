import hashlib
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from journal.models import JournalLog
from koleksi.models import Tanaman
from koleksi import services as perenual

from .models import WateringSchedule

OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HORIZON_DAYS = 7
RAIN_SKIP_MM = 5
WEATHER_CACHE_SECONDS = 20 * 60
WEATHER_STALE_SECONDS = 24 * 60 * 60


def _finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _bounded_number(value, minimum, maximum):
    number = _finite_number(value)
    return number if number is not None and minimum <= number <= maximum else None


def _cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        return None


def _cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception:
        # Caching is optional; weather providers remain usable without the cache.
        pass


def _decimal(value):
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _parse_water_interval(water_level):
    if not isinstance(water_level, str) or not water_level.strip():
        return None
    normalized = water_level.strip().lower()
    if normalized in ("none", "tidak perlu", "tidak perlu penyiraman", "no watering"):
        return 0
    if any(term in normalized for term in ("daily", "setiap hari", "frequent", "sering")):
        return 2
    if any(term in normalized for term in ("weekly", "mingguan", "minimum", "sedikit", "jarang", "rare")):
        return 7
    if any(term in normalized for term in ("average", "rata-rata", "moderate", "sedang", "occasional")):
        return 4
    return None


def _water_interval(plant):
    """Use valid Perenual guidance, then saved species guidance, then a safe default."""
    saved_interval = _parse_water_interval(plant.penyiraman)
    if plant.spesies_id and plant.spesies_id > 0 and getattr(settings, "PERENUAL_API_KEY", ""):
        try:
            species = perenual.ambil_spesies(plant.spesies_id)
            api_interval = _parse_water_interval(species.get("penyiraman")) if species else None
            if api_interval is not None:
                return None if api_interval == 0 else api_interval
        except Exception:
            # The saved species guide remains available when Perenual is down or malformed.
            pass

    if saved_interval == 0:
        return None
    return saved_interval or 4


def _openweather_forecast(city, api_key, today, latitude=None, longitude=None):
    params = {"appid": api_key, "units": "metric"}
    if latitude is not None and longitude is not None:
        params.update({"lat": latitude, "lon": longitude})
    else:
        params["q"] = city
    response = requests.get(
        OPENWEATHER_FORECAST_URL,
        params=params,
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or str(payload.get("cod", "200")) != "200":
        raise ValueError("Respons OpenWeather tidak valid.")
    forecast_entries = payload.get("list")
    if not isinstance(forecast_entries, list):
        raise ValueError("Data prakiraan OpenWeather tidak tersedia.")

    local_tz = ZoneInfo(settings.TIME_ZONE)
    grouped = defaultdict(lambda: {"rain": 0.0, "temps": [], "humidities": []})
    has_measurements = False
    for entry in forecast_entries:
        if not isinstance(entry, dict):
            continue
        timestamp = _finite_number(entry.get("dt"))
        if timestamp is None:
            continue
        try:
            forecast_day = datetime.fromtimestamp(timestamp, tz=local_tz).date()
        except (OverflowError, OSError, ValueError):
            continue
        if not today <= forecast_day <= today + timedelta(days=HORIZON_DAYS - 1):
            continue
        values = grouped[forecast_day]
        rain = entry.get("rain") if isinstance(entry.get("rain"), dict) else {}
        rain_amount = _bounded_number(rain.get("3h"), 0, 1000)
        if rain_amount is not None:
            values["rain"] += rain_amount
            has_measurements = True
        main = entry.get("main") if isinstance(entry.get("main"), dict) else {}
        temp = _bounded_number(main.get("temp_max"), -90, 70)
        humidity = _bounded_number(main.get("humidity"), 0, 100)
        if temp is not None:
            values["temps"].append(temp)
            has_measurements = True
        if humidity is not None:
            values["humidities"].append(humidity)
            has_measurements = True

    forecast = {
        day: {
            "rain": values["rain"],
            "temp_max": max(values["temps"]) if values["temps"] else None,
            "humidity": sum(values["humidities"]) / len(values["humidities"]) if values["humidities"] else None,
        }
        for day, values in grouped.items()
    }
    if not forecast or not has_measurements:
        raise ValueError("OpenWeather tidak mengembalikan prakiraan yang bisa digunakan.")
    return forecast


def _open_meteo_forecast(city, today, latitude=None, longitude=None):
    if latitude is None or longitude is None:
        location_response = requests.get(
            OPEN_METEO_GEOCODING_URL,
            params={"name": city, "count": 1, "language": "id", "format": "json"},
            timeout=8,
        )
        location_response.raise_for_status()
        location_payload = location_response.json()
        locations = location_payload.get("results", []) if isinstance(location_payload, dict) else []
        if not locations:
            raise ValueError("Lokasi tidak ditemukan.")
        location = locations[0]
        if not isinstance(location, dict):
            raise ValueError("Koordinat lokasi tidak valid.")
        latitude = _bounded_number(location.get("latitude"), -90, 90)
        longitude = _bounded_number(location.get("longitude"), -180, 180)
        if latitude is None or longitude is None:
            raise ValueError("Koordinat lokasi tidak valid.")

    forecast_response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "precipitation_sum,temperature_2m_max,relative_humidity_2m_mean",
            "forecast_days": HORIZON_DAYS,
            "timezone": settings.TIME_ZONE,
        },
        timeout=8,
    )
    forecast_response.raise_for_status()
    payload = forecast_response.json()
    daily = payload.get("daily", {}) if isinstance(payload, dict) else {}
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise ValueError("Data harian Open-Meteo tidak valid.")

    rain_values = daily.get("precipitation_sum")
    temp_values = daily.get("temperature_2m_max")
    humidity_values = daily.get("relative_humidity_2m_mean")
    if not any(isinstance(values, list) and values for values in (rain_values, temp_values, humidity_values)):
        raise ValueError("Open-Meteo tidak mengembalikan data cuaca harian.")

    def value_at(values, index):
        if not isinstance(values, list) or index >= len(values):
            return None
        return _finite_number(values[index])

    forecast = {}
    for index, day_text in enumerate(daily["time"]):
        try:
            day = date.fromisoformat(day_text)
        except (TypeError, ValueError):
            continue
        if day < today:
            continue
        rain = _bounded_number(value_at(rain_values, index), 0, 1000)
        temp = _bounded_number(value_at(temp_values, index), -90, 70)
        humidity = _bounded_number(value_at(humidity_values, index), 0, 100)
        forecast[day] = {"rain": rain, "temp_max": temp, "humidity": humidity}
    if not forecast or not any(any(value is not None for value in weather.values()) for weather in forecast.values()):
        raise ValueError("Open-Meteo tidak mengembalikan tanggal prakiraan yang valid.")
    return forecast


def get_weather_forecast(city, today=None, latitude=None, longitude=None):
    """Get daily rain and heat values, preferring configured OpenWeather data."""
    today = today or timezone.localdate()
    city = city.strip() if isinstance(city, str) else ""
    latitude = _finite_number(latitude) if latitude is not None else None
    longitude = _finite_number(longitude) if longitude is not None else None
    if (
        latitude is not None and longitude is not None
        and (-90 <= latitude <= 90 and -180 <= longitude <= 180)
    ):
        has_coordinates = True
    else:
        latitude = longitude = None
        has_coordinates = False
    if not city and not has_coordinates:
        return {}, "Tidak tersedia", "Masukkan kota untuk mengambil prakiraan cuaca."

    location_key = (
        f"coords:{latitude:.3f}:{longitude:.3f}"
        if has_coordinates else f"city:{city.casefold()}"
    )
    location_digest = hashlib.sha256(location_key.encode("utf-8")).hexdigest()
    cache_digest = hashlib.sha256(f"{today.isoformat()}:{location_key}".encode("utf-8")).hexdigest()
    cache_key = f"schedule:weather:{cache_digest}"
    stale_key = f"schedule:weather:stale:{location_digest}"
    cached = _cache_get(cache_key)
    if cached:
        forecast, provider = cached
        return forecast, provider, ""

    api_key = getattr(settings, "OPENWEATHER_API_KEY", "")
    if api_key:
        try:
            forecast = _openweather_forecast(city, api_key, today, latitude, longitude)
            provider = "OpenWeather"
            _cache_set(cache_key, (forecast, provider), WEATHER_CACHE_SECONDS)
            _cache_set(stale_key, (forecast, provider), WEATHER_STALE_SECONDS)
            return forecast, provider, ""
        except Exception:
            # Keep the calendar useful if OpenWeather is temporarily unavailable.
            try:
                forecast = _open_meteo_forecast(city, today, latitude, longitude)
                provider = "Open-Meteo"
                _cache_set(cache_key, (forecast, provider), WEATHER_CACHE_SECONDS)
                _cache_set(stale_key, (forecast, provider), WEATHER_STALE_SECONDS)
                return forecast, provider, "Prakiraan OpenWeather tidak tersedia; memakai prakiraan alternatif."
            except Exception:
                pass
    else:
        try:
            forecast = _open_meteo_forecast(city, today, latitude, longitude)
            provider = "Open-Meteo"
            _cache_set(cache_key, (forecast, provider), WEATHER_CACHE_SECONDS)
            _cache_set(stale_key, (forecast, provider), WEATHER_STALE_SECONDS)
            return forecast, provider, ""
        except Exception:
            pass

    stale = _cache_get(stale_key)
    if stale:
        forecast, provider = stale
        forecast = {
            day: values
            for day, values in forecast.items()
            if today <= day <= today + timedelta(days=HORIZON_DAYS - 1)
        }
        if forecast:
            return forecast, f"{provider} (tersimpan)", "Prakiraan terbaru gagal dimuat; memakai data cuaca tersimpan selama maksimal 24 jam."
    return {}, "Tidak tersedia", "Prakiraan cuaca belum dapat dimuat. Jadwal memakai panduan kebutuhan air tanaman."


def _recommendation(target_day, forecast):
    """Move watering away from heavy rain and note hot, dry conditions."""
    weather = forecast.get(target_day)
    if not weather:
        return target_day, "Jadwal mengikuti kebutuhan air spesies.", None, None

    rain = _decimal(weather.get("rain"))
    temp = _decimal(weather.get("temp_max"))
    humidity = _decimal(weather.get("humidity"))
    if rain is not None and rain >= RAIN_SKIP_MM:
        for offset in (1, 2):
            dry_day = target_day + timedelta(days=offset)
            dry_weather = forecast.get(dry_day)
            dry_rain = _decimal(dry_weather.get("rain")) if dry_weather else None
            if dry_weather and (dry_rain is None or dry_rain < RAIN_SKIP_MM):
                return (
                    dry_day,
                    f"Penyiraman digeser karena prakiraan hujan {rain:.1f} mm pada jadwal awal.",
                    _decimal(dry_weather.get("rain")),
                    _decimal(dry_weather.get("temp_max")),
                )
        return (
            target_day,
            f"Potensi hujan {rain:.1f} mm. Periksa media tanam sebelum menyiram.",
            rain,
            temp,
        )

    if temp is not None and temp >= 32 and humidity is not None and humidity < 45:
        note = "Cuaca panas dan kering; periksa kelembapan media lebih awal."
    elif rain is not None and rain > 0:
        note = f"Hujan diperkirakan {rain:.1f} mm; periksa media tanam sebelum menyiram."
    else:
        note = "Jadwal mengikuti kebutuhan air spesies dan prakiraan cuaca."
    return target_day, note, rain, temp


def synchronize(owner, city, latitude=None, longitude=None):
    """Refresh the owner's upcoming watering recommendations for one week."""
    today = timezone.localdate()
    last_day = today + timedelta(days=HORIZON_DAYS - 1)
    plants = list(Tanaman.objects.filter(pemilik=owner).order_by("nama_panggilan"))
    forecast, provider, weather_message = get_weather_forecast(city, today, latitude, longitude)
    intervals = {plant.pk: _water_interval(plant) for plant in plants}

    last_watered = dict(
        JournalLog.objects.filter(
            owner=owner,
            plant__in=plants,
            activity=JournalLog.Activity.WATERING,
        ).values("plant_id").annotate(last_at=Max("occurred_at")).values_list("plant_id", "last_at")
    )

    plans = []
    for plant in plants:
        last_at = last_watered.get(plant.pk)
        last_watered_day = timezone.localtime(last_at).date() if last_at else None
        interval = intervals[plant.pk]
        if interval is None:
            continue
        due_day = (last_watered_day + timedelta(days=interval)) if last_watered_day else today
        due_day = max(due_day, today)

        while due_day <= last_day:
            planned_day, note, rain, temp = _recommendation(due_day, forecast)
            if planned_day > last_day:
                planned_day = last_day
                note = "Jadwal dipindahkan ke akhir rentang prakiraan; periksa media tanam sebelum menyiram."
                weather = forecast.get(planned_day) or {}
                rain = _decimal(weather.get("rain"))
                temp = _decimal(weather.get("temp_max"))

            plans.append((plant, planned_day, note, rain, temp))
            due_day = planned_day + timedelta(days=interval)

    scheduled_ids = set()
    with transaction.atomic():
        for plant, planned_day, note, rain, temp in plans:
            reminder, created = WateringSchedule.objects.get_or_create(
                owner=owner,
                plant=plant,
                scheduled_for=planned_day,
                defaults={
                    "status": WateringSchedule.Status.PLANNED,
                    "recommendation": note,
                    "rainfall_mm": rain,
                    "temperature_max_c": temp,
                    "weather_source": provider,
                },
            )
            if not created and reminder.status == WateringSchedule.Status.PLANNED:
                reminder.recommendation = note
                reminder.rainfall_mm = rain
                reminder.temperature_max_c = temp
                reminder.weather_source = provider
                reminder.save(update_fields=[
                    "recommendation", "rainfall_mm", "temperature_max_c", "weather_source", "updated_at",
                ])
            scheduled_ids.add(reminder.pk)

        # Remove stale generated reminders, while preserving completed care.
        stale = WateringSchedule.objects.filter(
            owner=owner,
            scheduled_for__range=(today, last_day),
            status=WateringSchedule.Status.PLANNED,
        )
        stale.exclude(pk__in=scheduled_ids).delete()

    return {
        "provider": provider,
        "weather_message": weather_message,
        "plant_count": len(plants),
        "schedule_count": len(scheduled_ids),
        "synced_at": timezone.now(),
    }


def schedule_groups(owner, *, days=HORIZON_DAYS, status="active", plant_id="", search=""):
    today = timezone.localdate()
    entries = WateringSchedule.objects.filter(
        owner=owner,
        scheduled_for__range=(today, today + timedelta(days=days - 1)),
    ).select_related("plant").only(
        "id",
        "scheduled_for",
        "status",
        "recommendation",
        "rainfall_mm",
        "temperature_max_c",
        "weather_source",
        "plant__id",
        "plant__nama_panggilan",
        "plant__nama_ilmiah",
        "plant__foto",
        "plant__lokasi",
    )
    if status == "active":
        entries = entries.exclude(status=WateringSchedule.Status.DISMISSED)
    elif status != "all":
        entries = entries.filter(status=status)
    if plant_id:
        entries = entries.filter(plant_id=plant_id)
    if search:
        entries = entries.filter(
            Q(plant__nama_panggilan__icontains=search)
            | Q(plant__nama_ilmiah__icontains=search)
        )
    groups = []
    for entry in entries:
        if not groups or groups[-1]["date"] != entry.scheduled_for:
            groups.append({"date": entry.scheduled_for, "entries": []})
        groups[-1]["entries"].append(entry)
    return groups
