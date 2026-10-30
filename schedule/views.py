import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from journal.models import JournalLog

from .models import WateringSchedule
from .services import HORIZON_DAYS, schedule_groups, synchronize


@login_required
def calendar(request):
    city = request.session.get("schedule_city", "Jakarta")
    entries = schedule_groups(request.user)
    return render(request, "schedule/calendar.html", {
        "schedule_groups": entries,
        "city": city,
        "latitude": request.session.get("schedule_latitude"),
        "longitude": request.session.get("schedule_longitude"),
        "has_coordinates": (
            request.session.get("schedule_latitude") is not None
            and request.session.get("schedule_longitude") is not None
        ),
        "horizon_days": HORIZON_DAYS,
        "planned_count": sum(
            entry.status == WateringSchedule.Status.PLANNED
            for group in entries for entry in group["entries"]
        ),
        "completed_count": sum(
            entry.status == WateringSchedule.Status.COMPLETED
            for group in entries for entry in group["entries"]
        ),
        "weather_provider": request.session.get("schedule_weather_provider", "Belum disinkronkan"),
        "last_synced": request.session.get("schedule_last_synced", ""),
        "has_synced": bool(request.session.get("schedule_last_synced")),
        "has_plants": request.user.koleksi_tanaman.exists(),
    })


@login_required
def synchronize_schedule(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    raw_latitude = request.POST.get("latitude", "").strip()
    raw_longitude = request.POST.get("longitude", "").strip()
    latitude = longitude = None
    if bool(raw_latitude) != bool(raw_longitude):
        messages.error(request, "Lokasi perangkat tidak lengkap. Coba pilih lokasi kembali atau masukkan kota.")
        return redirect("schedule:calendar")

    if raw_latitude and raw_longitude:
        try:
            latitude = float(raw_latitude)
            longitude = float(raw_longitude)
        except ValueError:
            messages.error(request, "Koordinat lokasi tidak valid. Coba pilih lokasi kembali.")
            return redirect("schedule:calendar")
        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            messages.error(request, "Koordinat lokasi berada di luar jangkauan yang valid.")
            return redirect("schedule:calendar")

    city = request.POST.get("city", "").strip()[:100]
    if latitude is not None:
        city = city or "Lokasi saya"
    elif not city:
        messages.error(request, "Masukkan kota atau pilih lokasi perangkat untuk memperbarui jadwal cuaca.")
        return redirect("schedule:calendar")

    request.session["schedule_city"] = city
    request.session["schedule_latitude"] = latitude
    request.session["schedule_longitude"] = longitude
    result = synchronize(request.user, city, latitude, longitude)
    request.session["schedule_weather_provider"] = result["provider"]
    request.session["schedule_last_synced"] = timezone.localtime(result["synced_at"]).strftime("%d/%m %H:%M")
    if not result["plant_count"]:
        messages.info(request, "Tambahkan tanaman ke koleksimu untuk membuat jadwal penyiraman.")
    elif result["weather_message"]:
        messages.warning(request, result["weather_message"])
        messages.success(request, f"Jadwal {result['schedule_count']} tanaman diperbarui untuk {city}.")
    else:
        messages.success(request, f"Jadwal {result['schedule_count']} tanaman diperbarui untuk {city}.")
    return redirect("schedule:calendar")


@login_required
def mark_complete(request, schedule_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    schedule = get_object_or_404(
        WateringSchedule.objects.select_related("plant"),
        pk=schedule_id,
        owner=request.user,
        plant__pemilik=request.user,
    )
    if schedule.status == WateringSchedule.Status.PLANNED:
        JournalLog.objects.create(
            owner=request.user,
            plant=schedule.plant,
            occurred_at=timezone.now(),
            plant_name=schedule.plant.nama_panggilan,
            plant_species=schedule.plant.nama_ilmiah,
            activity=JournalLog.Activity.WATERING,
            notes="Penyiraman dicatat dari jadwal perawatan Floranity.",
        )
        schedule.status = WateringSchedule.Status.COMPLETED
        schedule.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Penyiraman {schedule.plant.nama_panggilan} dicatat di jurnal.")
    return redirect("schedule:calendar")
