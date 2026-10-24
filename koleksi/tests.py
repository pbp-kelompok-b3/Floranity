from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from .models import Tanaman


class KoleksiDanKatalogTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_katalog_list_view(self):
        url = reverse("koleksi:katalog")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/katalog_list.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Katalog Tanaman")
        self.assertContains(response, "koleksi/css/koleksi.css")

    def test_katalog_detail_view(self):
        url = reverse("koleksi:katalog_detail", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/katalog_detail.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Kebutuhan cahaya")

    def test_koleksi_list_view(self):
        url = reverse("koleksi:daftar")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_list.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Koleksi Saya")

    def test_koleksi_detail_view(self):
        url = reverse("koleksi:detail", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_detail.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Monstera meja belajar")

    def test_koleksi_tambah_view(self):
        url = reverse("koleksi:tambah")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_form.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Tambah tanaman")

    def test_koleksi_ubah_view(self):
        url = reverse("koleksi:ubah", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_form.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Ubah info tanaman")

    def test_koleksi_hapus_view(self):
        url = reverse("koleksi:hapus", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_hapus.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Hapus tanaman")

    def test_terjemahan_perenual(self):
        from . import services

        # Test sunlight translation
        self.assertEqual(services._terjemahkan(["full sun"], services.TERJEMAHAN_CAHAYA), "Matahari Penuh")
        self.assertEqual(services._terjemahkan(["full sun", "part shade"], services.TERJEMAHAN_CAHAYA), "Matahari Penuh, Teduh Sebagian")
        self.assertEqual(services._terjemahkan("full sun, part shade", services.TERJEMAHAN_CAHAYA), "Matahari Penuh, Teduh Sebagian")

        # Test watering translation
        self.assertEqual(services._terjemahkan("Average", services.TERJEMAHAN_AIR), "Rata-rata")
        self.assertEqual(services._terjemahkan("Frequent", services.TERJEMAHAN_AIR), "Sering")
        self.assertEqual(services._terjemahkan("minimum", services.TERJEMAHAN_AIR), "Sedikit")

        # Test care level translation
        self.assertEqual(services._terjemahkan("Medium", services.TERJEMAHAN_KESULITAN), "Sedang")
        self.assertEqual(services._terjemahkan("Low", services.TERJEMAHAN_KESULITAN), "Mudah")
        self.assertEqual(services._terjemahkan("High", services.TERJEMAHAN_KESULITAN), "Sulit")

        # Test cycle translation
        self.assertEqual(services._terjemahkan("Perennial", services.TERJEMAHAN_SIKLUS), "Tahunan")
        self.assertEqual(services._terjemahkan("Annual", services.TERJEMAHAN_SIKLUS), "Semusim")

        # Test indoor translation
        self.assertEqual(services._dalam_ruangan(False), "Tidak")
        self.assertEqual(services._dalam_ruangan(True), "Ya")

        # Test _bentuk_spesies formatting
        raw_item = {
            "id": 2,
            "common_name": "Pyramidalis Silver Fir",
            "scientific_name": ["Abies alba 'Pyramidalis'"],
            "family": "Pinaceae",
            "sunlight": ["full sun"],
            "watering": "Average",
            "care_level": "Medium",
            "cycle": "Perennial",
            "indoor": False,
            "description": "Pyramidalis Silver Fir is an amazing coniferous tree.",
        }
        spesies = services._bentuk_spesies(raw_item)
        self.assertEqual(spesies["cahaya"], "Matahari Penuh")
        self.assertEqual(spesies["penyiraman"], "Rata-rata")
        self.assertEqual(spesies["tingkat_kesulitan"], "Sedang")
        self.assertEqual(spesies["siklus"], "Tahunan")
        self.assertEqual(spesies["famili"], "Pinaceae")
        self.assertEqual(spesies["dalam_ruangan"], "Tidak")
        self.assertEqual(spesies["deskripsi"], "Pyramidalis Silver Fir is an amazing coniferous tree.")

    def test_tanaman_model(self):
        user = User.objects.create_user(username="testuser", password="password123")
        tanaman = Tanaman.objects.create(
            pemilik=user,
            spesies_id=1,
            nama_panggilan="Monstera Cantik",
            nama_ilmiah="Monstera deliciosa",
            lokasi="Balkon Depan",
            cahaya="Matahari Sebagian",
            penyiraman="Sedang",
        )
        self.assertEqual(str(tanaman), "Monstera Cantik")
        self.assertEqual(tanaman.pemilik.username, "testuser")
