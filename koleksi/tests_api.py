from datetime import date

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from koleksi.models import JurnalPertumbuhan, Tanaman


class KoleksiAPITest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", password="test-password"
        )
        self.other_user = User.objects.create_user(
            username="other", password="test-password"
        )
        self.tanaman = Tanaman.objects.create(
            pemilik=self.owner,
            nama_panggilan="Monstera Ruang Tamu",
            nama_ilmiah="Monstera deliciosa",
            lokasi="Ruang Tamu",
        )
        self.katalog_list_url = reverse("koleksi_api:katalog-list")
        self.list_url = reverse("koleksi_api:tanaman-list")
        self.detail_url = reverse(
            "koleksi_api:tanaman-detail", args=[self.tanaman.id]
        )
        self.jurnal_url = reverse("koleksi_api:jurnal-list", args=[self.tanaman.id])
        self.payload = {
            "nama_panggilan": "Lidah Mertua",
            "nama_ilmiah": "Sansevieria trifasciata",
            "lokasi": "Balkon",
            "catatan": "Tahan kering",
        }

    def test_public_katalog_list(self):
        response = self.client.get(self.katalog_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_guest_cannot_access_koleksi(self):
        self.assertEqual(
            self.client.get(self.list_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(self.list_url, self.payload, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_owner_can_list_create_and_search(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.tanaman.id)

        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tanaman.objects.filter(pk=response.data["id"]).exists())

        search_res = self.client.get(self.list_url, {"q": "Lidah"})
        self.assertEqual(len(search_res.data), 1)

    def test_other_user_cannot_access_or_modify_tanaman(self):
        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(
            self.client.get(self.detail_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(
                self.detail_url, {"nama_panggilan": "Hack"}, format="json"
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.detail_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_validation_rejects_empty_nama_panggilan(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.list_url,
            {**self.payload, "nama_panggilan": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nama_panggilan", response.data)

    def test_patch_put_and_delete(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.detail_url, {"lokasi": "Teras"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tanaman.refresh_from_db()
        self.assertEqual(self.tanaman.lokasi, "Teras")

        response = self.client.put(
            self.detail_url, self.payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tanaman.objects.filter(pk=self.tanaman.id).exists())

    def test_jurnal_list_and_create(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.jurnal_url,
            {"tanggal": str(date.today()), "catatan": "Daun baru muncul"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JurnalPertumbuhan.objects.count(), 1)

        list_res = self.client.get(self.jurnal_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 1)

    def test_session_write_without_csrf_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(
            client.login(username="owner", password="test-password")
        )
        response = client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
