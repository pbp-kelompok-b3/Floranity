import uuid

from django.conf import settings
from django.db import models


class JournalLog(models.Model):
    class Activity(models.TextChoices):
        WATERING = "watering", "Watering"
        FERTILIZING = "fertilizing", "Fertilizing"
        PRUNING = "pruning", "Pruning"
        REPOTTING = "repotting", "Repotting"
        GROWTH = "growth", "Growth update"
        OTHER = "other", "Other"

    class HealthStatus(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        NEEDS_ATTENTION = "needs_attention", "Needs attention"
        RECOVERING = "recovering", "Recovering"
        UNKNOWN = "unknown", "Not checked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journal_logs",
    )
    plant = models.ForeignKey(
        "koleksi.Tanaman",
        on_delete=models.CASCADE,
        related_name="journal_logs",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    occurred_at = models.DateTimeField(help_text="When the care or growth event happened.")

    plant_name = models.CharField(max_length=150)
    plant_species = models.CharField(max_length=200, blank=True)
    plant_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="For example: indoor, outdoor, succulent, or bonsai.",
    )

    activity = models.CharField(max_length=20, choices=Activity.choices)
    water_volume_ml = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Water used in milliliters, when applicable.",
    )
    fertilizer_type = models.CharField(max_length=120, blank=True)
    health_status = models.CharField(
        max_length=20, choices=HealthStatus.choices, default=HealthStatus.UNKNOWN,
    )
    health_tags = models.CharField(
        max_length=250, blank=True,
        help_text="Optional comma-separated observations, such as yellow leaves or new growth.",
    )
    weather_temperature_c = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    weather_humidity_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    weather_rainfall_mm = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
    )
    notes = models.TextField(blank=True)
    photo = models.FileField(upload_to="journal/photos/", blank=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self):
        return f"{self.plant_name}: {self.get_activity_display()} ({self.occurred_at:%Y-%m-%d})"
