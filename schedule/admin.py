from django.contrib import admin

from .models import WateringSchedule


@admin.register(WateringSchedule)
class WateringScheduleAdmin(admin.ModelAdmin):
    list_display = ("plant", "owner", "scheduled_for", "status", "weather_source")
    list_filter = ("status", "scheduled_for", "weather_source")
    search_fields = ("plant__nama_panggilan", "plant__nama_ilmiah", "owner__username")
