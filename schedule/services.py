from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
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


def _decimal(value):
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _water_interval(plant):
    """Map Perenual's care level (or the saved species guide) to days."""
    water_level = plant.penyiraman or ""
    if plant.spesies_id and getattr(settings, "PERENUAL_API_KEY", ""):
        try:
            species = perenual.ambil_spesies(plant.spesies_id)
            if species and species.get("penyiraman"):
                water_level = species["penyiraman"]
        except Exception:
            pass

    normalized = water_level.strip().lower()
    if normalized in ("none", "tidak perlu", "tidak perlu penyiraman", "no watering"):
        return None
    if any(term in normalized for term in ("daily", "setiap hari", "frequent", "sering")):
        return 2
    if any(term in normalized for term in ("weekly", "mingguan", "minimum", "sedikit", "jarang", "rare")):
        return 7
    if any(term in normalized for term in ("average", "rata-rata", "moderate", "sedang", "occasional")):
        return 4
    return 4


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
    local_tz = ZoneInfo(settings.TIME_ZONE)
    grouped = defaultdict(lambda: {"rain": 0.0, "temps": [], "humidities": []})
    for entry in payload.get("list", []):
        forecast_day = datetime.fromtimestamp(entry["dt"], tz=local_tz).date()
        if not today <= forecast_day <= today + timedelta(days=HORIZON_DAYS - 1):
            continue
        values = grouped[forecast_day]
        values["rain"] += float(entry.get("rain", {}).get("3h", 0) or 0)
        main = entry.get("main", {})
        if main.get("temp_max") is not None:
            values["temps"].append(float(main["temp_max"]))
        if main.get("humidity") is not None:
            values["humidities"].append(float(main["humidity"]))

    forecast = {
        day: {
            "rain": values["rain"],
            "temp_max": max(values["temps"]) if values["temps"] else None,
            "humidity": sum(values["humidities"]) / len(values["humidities"]) if values["humidities"] else None,
        }
        for day, values in grouped.items()
    }
    return forecast


def _open_meteo_forecast(city, today, latitude=None, longitude=None):
    if latitude is None or longitude is None:
        location_response = requests.get(
            OPEN_METEO_GEOCODING_URL,
            params={"name": city, "count": 1, "language": "id", "format": "json"},
            timeout=8,
        )
        location_response.raise_for_status()
        locations = location_response.json().get("results", [])
        if not locations:
            raise ValueError("Lokasi tidak ditemukan.")
        location = locations[0]
        latitude = location["latitude"]
        longitude = location["longitude"]

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
    daily = forecast_response.json().get("daily", {})
    forecast = {}
    for index, day_text in enumerate(daily.get("time", [])):
        day = date.fromisoformat(day_text)
        if day < today:
            continue
        forecast[day] = {
            "rain": (daily.get("precipitation_sum") or [])[index],
            "temp_max": (daily.get("temperature_2m_max") or [])[index],
            "humidity": (daily.get("relative_humidity_2m_mean") or [])[index],
        }
    return forecast


def get_weather_forecast(city, today=None, latitude=None, longitude=None):
    """Get daily rain and heat values, preferring configured OpenWeather data."""
    today = today or timezone.localdate()
    city = city.strip()
    has_coordinates = latitude is not None and longitude is not None
    if not city and not has_coordinates:
        return {}, "Tidak tersedia", "Masukkan kota untuk mengambil prakiraan cuaca."

    api_key = getattr(settings, "OPENWEATHER_API_KEY", "")
    if api_key:
        try:
            return _openweather_forecast(city, api_key, today, latitude, longitude), "OpenWeather", ""
        except (requests.RequestException, ValueError, KeyError, TypeError):
            # Keep the calendar useful if OpenWeather is temporarily unavailable.
            try:
                return _open_meteo_forecast(city, today, latitude, longitude), "Open-Meteo", "Prakiraan OpenWeather tidak tersedia; memakai prakiraan alternatif."
            except (requests.RequestException, ValueError, KeyError, TypeError):
                return {}, "Tidak tersedia", "Prakiraan cuaca belum dapat dimuat. Jadwal memakai panduan kebutuhan air tanaman."

    try:
        return _open_meteo_forecast(city, today, latitude, longitude), "Open-Meteo", ""
    except (requests.RequestException, ValueError, KeyError, TypeError):
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
