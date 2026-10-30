from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from journal.models import JournalLog
from koleksi.models import Tanaman

from .models import WateringSchedule
from .services import HORIZON_DAYS, _recommendation, get_weather_forecast


class ScheduleFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="schedule-owner", password="test-pass")
        self.plant = Tanaman.objects.create(
            pemilik=self.owner,
            nama_panggilan="Monstera",
            nama_ilmiah="Monstera deliciosa",
            penyiraman="Rata-rata",
        )
        self.client.force_login(self.owner)

    def make_schedule(self, scheduled_for):
        return WateringSchedule.objects.create(
            owner=self.owner,
            plant=self.plant,
            scheduled_for=scheduled_for,
            recommendation="Periksa media tanam.",
        )

    def test_future_schedule_cannot_be_completed_early(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        entry = self.make_schedule(tomorrow)

        response = self.client.post(
            reverse("schedule:bulk_action"),
            {"single_complete": str(entry.pk)},
            follow=True,
        )

        entry.refresh_from_db()
        self.assertEqual(entry.status, WateringSchedule.Status.PLANNED)
        self.assertFalse(JournalLog.objects.filter(owner=self.owner).exists())
        self.assertContains(response, "Penyiraman hanya dapat dicatat pada atau setelah tanggal jadwal.")

    def test_calendar_shows_future_item_as_scheduled_without_completion_button(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        entry = self.make_schedule(tomorrow)

        response = self.client.get(reverse("schedule:calendar"))

        self.assertContains(response, "Terjadwal")
        self.assertNotContains(response, f'name="single_complete" value="{entry.pk}"')

    def test_due_schedule_completion_adds_one_watering_journal_entry(self):
        entry = self.make_schedule(timezone.localdate())

        response = self.client.post(
            reverse("schedule:bulk_action"),
            {"single_complete": str(entry.pk)},
            follow=True,
        )

        entry.refresh_from_db()
        self.assertEqual(entry.status, WateringSchedule.Status.COMPLETED)
        self.assertEqual(
            JournalLog.objects.filter(
                owner=self.owner,
                plant=self.plant,
                activity=JournalLog.Activity.WATERING,
            ).count(),
            1,
        )
        self.assertContains(response, "1 penyiraman dicatat di jurnal.")


class WeatherFallbackTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_unknown_rainfall_does_not_make_a_rescheduled_day_look_dry(self):
        today = timezone.localdate()
        forecast = {
            today: {"rain": 8, "temp_max": 24, "humidity": 60},
            today + timedelta(days=1): {"rain": None, "temp_max": 24, "humidity": 60},
        }

        planned_day, _, rain, _ = _recommendation(today, forecast)

        self.assertEqual(planned_day, today)
        self.assertEqual(rain, 8)

    @override_settings(OPENWEATHER_API_KEY="configured")
    @patch("schedule.services._open_meteo_forecast")
    @patch("schedule.services._openweather_forecast")
    def test_fills_openweather_five_day_horizon_with_open_meteo(self, openweather, open_meteo):
        today = timezone.localdate()
        openweather.return_value = {
            today + timedelta(days=offset): {"rain": 0, "temp_max": 24, "humidity": 60}
            for offset in range(5)
        }
        open_meteo.return_value = {
            today + timedelta(days=offset): {"rain": 0, "temp_max": 25, "humidity": 55}
            for offset in range(HORIZON_DAYS)
        }

        forecast, provider, message = get_weather_forecast("Jakarta", today)

        self.assertEqual(len(forecast), HORIZON_DAYS)
        self.assertEqual(provider, "OpenWeather + Open-Meteo")
        self.assertEqual(message, "")
        self.assertEqual(forecast[today + timedelta(days=4)]["temp_max"], 24)
        self.assertEqual(forecast[today + timedelta(days=5)]["temp_max"], 25)

