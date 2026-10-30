import math
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from journal.models import JournalLog
from koleksi.decorators import rate_limit_sensitive

from .models import WateringSchedule
from .services import HORIZON_DAYS, schedule_groups, synchronize


@login_required
@require_GET
def calendar(request):
    city = request.session.get("schedule_city", "Jakarta")
    today = timezone.localdate()
    plant_options = list(
        request.user.koleksi_tanaman.only("id", "nama_panggilan").order_by("nama_panggilan")
    )
    allowed_days = {"1", "3", "7"}
    allowed_statuses = {"active", "planned", "completed", "dismissed", "all"}
    days = request.GET.get("days", "7")
    status = request.GET.get("status", "active")
    query = request.GET.get("q", "").strip()[:80]
    plant_id = request.GET.get("plant", "")

    if days not in allowed_days:
        days = "7"
    if status not in allowed_statuses:
        status = "active"
    if (
        not plant_id.isdigit()
        or len(plant_id) > 18
        or plant_id not in {str(plant.pk) for plant in plant_options}
    ):
        plant_id = ""

    entries = schedule_groups(
        request.user,
        days=int(days),
        status=status,
        plant_id=plant_id,
        search=query,
    )
    summary = WateringSchedule.objects.filter(
        owner=request.user,
        scheduled_for__range=(today, today + timedelta(days=HORIZON_DAYS - 1)),
    ).aggregate(
        planned=Count("pk", filter=Q(status=WateringSchedule.Status.PLANNED)),
        completed=Count("pk", filter=Q(status=WateringSchedule.Status.COMPLETED)),
        dismissed=Count("pk", filter=Q(status=WateringSchedule.Status.DISMISSED)),
    )
    return render(request, "schedule/calendar.html", {
        "schedule_groups": entries,
        "city": city,
        "plant_options": plant_options,
        "filter_days": days,
        "filter_status": status,
        "filter_plant": int(plant_id) if plant_id else None,
        "filter_query": query,
        "has_filters": bool(query or plant_id or days != "7" or status != "active"),
        "latitude": request.session.get("schedule_latitude"),
        "longitude": request.session.get("schedule_longitude"),
        "has_coordinates": (
            request.session.get("schedule_latitude") is not None
            and request.session.get("schedule_longitude") is not None
        ),
        "horizon_days": HORIZON_DAYS,
        "planned_count": summary["planned"],
        "completed_count": summary["completed"],
        "dismissed_count": summary["dismissed"],
        "weather_provider": request.session.get("schedule_weather_provider", "Belum disinkronkan"),
        "last_synced": request.session.get("schedule_last_synced", ""),
        "has_synced": bool(request.session.get("schedule_last_synced")),
        "has_plants": request.user.koleksi_tanaman.exists(),
    })


@login_required
@require_POST
@rate_limit_sensitive(max_requests=8, window_seconds=60, key_prefix="schedule")
def synchronize_schedule(request):
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
        messages.success(request, f"{result['schedule_count']} pengingat diperbarui untuk {city}.")
    else:
        messages.success(request, f"{result['schedule_count']} pengingat diperbarui untuk {city}.")
    return redirect("schedule:calendar")


@login_required
@require_POST
@rate_limit_sensitive(max_requests=15, window_seconds=60, key_prefix="schedule")
def bulk_action(request):
    action = request.POST.get("action", "")
    raw_ids = request.POST.getlist("schedule_ids")
    single_complete = request.POST.get("single_complete", "")
    if single_complete:
        action = "complete"
        raw_ids = [single_complete]
    allowed_actions = {"complete", "dismiss", "restore"}
    if action not in allowed_actions:
        messages.error(request, "Pilih tindakan jadwal yang valid.")
        return redirect("schedule:calendar")

    if not raw_ids or len(raw_ids) > 100 or any(not value.isdigit() or len(value) > 18 for value in raw_ids):
        messages.error(request, "Pilih maksimal 100 jadwal yang valid.")
        return redirect("schedule:calendar")

    schedule_ids = {int(value) for value in raw_ids}
    expected_status = (
        WateringSchedule.Status.DISMISSED if action == "restore"
        else WateringSchedule.Status.PLANNED
    )
    eligible = WateringSchedule.objects.filter(
        owner=request.user,
        plant__pemilik=request.user,
        pk__in=schedule_ids,
        status=expected_status,
    )

    with transaction.atomic():
        selected = list(eligible.select_for_update().select_related("plant"))
        if action == "complete":
            now = timezone.now()
            logs = []
            updated_count = 0
            for entry in selected:
                updated = WateringSchedule.objects.filter(
                    pk=entry.pk,
                    owner=request.user,
                    plant__pemilik=request.user,
                    status=WateringSchedule.Status.PLANNED,
                ).update(status=WateringSchedule.Status.COMPLETED, updated_at=now)
                if updated:
                    updated_count += 1
                    logs.append(JournalLog(
                        owner=request.user,
                        plant=entry.plant,
                        occurred_at=now,
                        plant_name=entry.plant.nama_panggilan,
                        plant_species=entry.plant.nama_ilmiah,
                        activity=JournalLog.Activity.WATERING,
                        notes="Penyiraman dicatat dari jadwal perawatan Floranity.",
                    ))
            if logs:
                JournalLog.objects.bulk_create(logs)
        else:
            target_status = (
                WateringSchedule.Status.DISMISSED if action == "dismiss"
                else WateringSchedule.Status.PLANNED
            )
            updated_count = eligible.update(status=target_status, updated_at=timezone.now())

    if not updated_count:
        messages.info(request, "Tidak ada jadwal terpilih yang memenuhi tindakan tersebut.")
    elif action == "complete":
        messages.success(request, f"{updated_count} penyiraman dicatat di jurnal.")
    elif action == "dismiss":
        messages.success(request, f"{updated_count} jadwal diarsipkan. Jadwal dapat dipulihkan melalui filter arsip.")
    else:
        messages.success(request, f"{updated_count} jadwal dipulihkan ke daftar aktif.")
    return redirect("schedule:calendar")
