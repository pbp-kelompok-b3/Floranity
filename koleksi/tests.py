from django.test import TestCase, Client
from django.urls import reverse


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
