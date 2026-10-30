from django.conf import settings
from django.db import models


class WateringSchedule(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Terjadwal"
        COMPLETED = "completed", "Selesai"
        DISMISSED = "dismissed", "Diarsipkan"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watering_schedules",
    )
    plant = models.ForeignKey(
        "koleksi.Tanaman",
        on_delete=models.CASCADE,
        related_name="watering_schedules",
    )
    scheduled_for = models.DateField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    recommendation = models.CharField(max_length=240, blank=True)
    rainfall_mm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    temperature_max_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weather_source = models.CharField(max_length=30, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_for", "plant__nama_panggilan"]
        constraints = [
            models.UniqueConstraint(
                fields=["plant", "scheduled_for"],
                name="unique_plant_watering_day",
            ),
        ]
        indexes = [
            models.Index(
                fields=["owner", "scheduled_for", "status"],
                name="sched_owner_day_status_idx",
            ),
        ]
        verbose_name = "Jadwal penyiraman"
        verbose_name_plural = "Jadwal penyiraman"

    def __str__(self):
        return f"{self.plant.nama_panggilan} — {self.scheduled_for:%Y-%m-%d}"
