from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from journal.forms import JournalLogForm
from journal.models import JournalLog
from koleksi.sample_data import SAMPLE_JOURNAL_LOG
from django.urls import reverse


class JournalLogTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="garden-owner", password="test-pass")
        self.other_owner = User.objects.create_user(username="other-owner", password="test-pass")
        self.client.force_login(self.owner)

    def make_log(self, *, owner=None, plant_name="Monstera meja belajar",
                 plant_species="Monstera deliciosa", occurred_at=None, notes=""):
        return JournalLog.objects.create(
            owner=owner or self.owner,
            occurred_at=occurred_at or timezone.now(),
            plant_name=plant_name,
            plant_species=plant_species,
            activity=JournalLog.Activity.WATERING,
            notes=notes,
        )

    def test_plant_detail_shows_only_matching_owners_entries_newest_first(self):
        now = timezone.now()
        older = self.make_log(occurred_at=now - timedelta(days=1), notes="Older entry")
        newer = self.make_log(occurred_at=now, notes="Newest entry")
        self.make_log(owner=self.other_owner, notes="Private entry")
        self.make_log(plant_name="Basil dapur", plant_species="Ocimum basilicum")

        response = self.client.get(reverse("koleksi:detail", args=[1]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["jurnal_list"]), [newer, older])
        self.assertContains(response, "Newest entry")
        self.assertNotContains(response, "Private entry")

    def test_plant_detail_uses_sample_journal_when_user_has_no_logs(self):
        response = self.client.get(reverse("koleksi:detail", args=[1]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sample_log"], SAMPLE_JOURNAL_LOG)
        self.assertContains(response, "Contoh data")

    def test_journal_form_saves_entry_for_owner(self):
        form = JournalLogForm(data={
            "plant_name": "Monstera meja belajar",
            "plant_species": "Monstera deliciosa",
            "plant_type": "Indoor",
            "activity": JournalLog.Activity.WATERING,
            "occurred_at": "2026-10-28T10:30",
            "water_volume_ml": "250.00",
            "fertilizer_type": "",
            "health_status": JournalLog.HealthStatus.HEALTHY,
            "health_tags": "New leaves",
            "weather_temperature_c": "",
            "weather_humidity_percent": "",
            "weather_rainfall_mm": "",
            "notes": "Watered this morning",
        })

        self.assertTrue(form.is_valid(), form.errors)
        log = form.save_for_owner(self.owner)

        self.assertEqual(log.owner, self.owner)
        self.assertEqual(log.water_volume_ml, Decimal("250.00"))
        self.assertEqual(log.notes, "Watered this morning")
