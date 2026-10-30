from django.contrib import admin
from .models import JournalLog


@admin.register(JournalLog)
class JournalLogAdmin(admin.ModelAdmin):
    list_display = ("plant_name", "plant_species", "activity", "occurred_at", "owner")
    list_filter = ("activity", "plant_type", "occurred_at")
    search_fields = ("plant_name", "plant_species", "owner__username")
