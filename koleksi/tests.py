from datetime import date
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from .forms import JurnalPertumbuhanForm, TanamanForm
from .models import JurnalPertumbuhan, Tanaman
from .seed import seed_sample_data_if_empty


@override_settings(PERENUAL_API_KEY="")
class KoleksiDanKatalogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.user2 = User.objects.create_user(username="testuser2", password="password123")
        seed_sample_data_if_empty()

    def test_katalog_list_view(self):
        url = reverse("koleksi:catalog")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/katalog_list.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Katalog Tanaman")
        self.assertContains(response, "koleksi/css/koleksi.css")

    def test_katalog_detail_view(self):
        url = reverse("koleksi:catalog_detail", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/katalog_detail.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Kebutuhan cahaya")

    def test_koleksi_list_view(self):
        url = reverse("koleksi:show_collection")
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
        url = reverse("koleksi:create_tanaman")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_form.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Tambah tanaman")

    def test_koleksi_ubah_view(self):
        url = reverse("koleksi:update", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_form.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Ubah info tanaman")

    def test_koleksi_hapus_view(self):
        url = reverse("koleksi:delete", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "koleksi/koleksi_hapus.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Hapus tanaman")

    def test_database_crud_flow(self):
        # 1. CREATE tanaman via POST
        data_baru = {
            "nama_panggilan": "Kaktus Mini",
            "spesies": "Cactaceae",
            "lokasi": "Meja Komputer",
            "catatan": "Jangan sering disiram",
        }
        res_create = self.client.post(reverse("koleksi:create_tanaman"), data_baru, follow=True)
        self.assertEqual(res_create.status_code, 200)
        messages_list = [m.message for m in get_messages(res_create.wsgi_request)]
        self.assertIn("Tanaman baru berhasil ditambahkan!", messages_list)
        kaktus = Tanaman.objects.get(nama_panggilan="Kaktus Mini")
        self.assertEqual(kaktus.nama_ilmiah, "Cactaceae")

        # 2. UPDATE tanaman via POST
        data_ubah = {
            "nama_panggilan": "Kaktus Mini Baru",
            "spesies": "Echinocactus",
            "lokasi": "Balkon Atas",
        }
        res_update = self.client.post(reverse("koleksi:update", args=[kaktus.id]), data_ubah, follow=True)
        self.assertEqual(res_update.status_code, 200)
        messages_list = [m.message for m in get_messages(res_update.wsgi_request)]
        self.assertIn("Info tanaman berhasil diperbarui!", messages_list)
        kaktus.refresh_from_db()
        self.assertEqual(kaktus.nama_panggilan, "Kaktus Mini Baru")
        self.assertEqual(kaktus.lokasi, "Balkon Atas")

        # 3. ADD JOURNAL via POST
        data_jurnal = {
            "tanggal": "2026-10-28",
            "catatan": "Tunas baru mulai tumbuh",
        }
        res_jurnal = self.client.post(reverse("koleksi:add_journal", args=[kaktus.id]), data_jurnal, follow=True)
        self.assertEqual(res_jurnal.status_code, 200)
        messages_list = [m.message for m in get_messages(res_jurnal.wsgi_request)]
        self.assertIn("Catatan jurnal berhasil ditambahkan!", messages_list)
        self.assertEqual(kaktus.jumlah_jurnal, 1)

        # 4. DELETE tanaman via POST
        res_delete = self.client.post(reverse("koleksi:delete", args=[kaktus.id]), follow=True)
        self.assertEqual(res_delete.status_code, 200)
        messages_list = [m.message for m in get_messages(res_delete.wsgi_request)]
        self.assertIn("Tanaman berhasil dihapus dari koleksi!", messages_list)
        self.assertFalse(Tanaman.objects.filter(id=kaktus.id).exists())

    def test_photo_upload_and_url(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Upload file foto langsung
        dummy_image = SimpleUploadedFile("test_tanaman.jpg", b"dummy_content", content_type="image/jpeg")
        data_foto_file = {
            "nama_panggilan": "Tanaman Berfoto File",
            "foto": dummy_image,
        }
        res1 = self.client.post(reverse("koleksi:create_tanaman"), data_foto_file, follow=True)
        self.assertEqual(res1.status_code, 200)
        t1 = Tanaman.objects.get(nama_panggilan="Tanaman Berfoto File")
        self.assertTrue(t1.foto.startswith("/media/tanaman/"))

        # Menggunakan foto URL
        data_foto_url = {
            "nama_panggilan": "Tanaman Berfoto URL",
            "foto_url": "https://images.unsplash.com/photo-example.jpg",
        }
        res2 = self.client.post(reverse("koleksi:create_tanaman"), data_foto_url, follow=True)
        self.assertEqual(res2.status_code, 200)
        t2 = Tanaman.objects.get(nama_panggilan="Tanaman Berfoto URL")
        self.assertEqual(t2.foto, "https://images.unsplash.com/photo-example.jpg")

    def test_security_object_level_authorization(self):
        # Buat tanaman milik self.user
        tanaman_user1 = Tanaman.objects.create(
            pemilik=self.user,
            nama_panggilan="Tanaman Rahasia User1",
            nama_ilmiah="Secretus plantus",
        )

        # 1. Login sebagai user lain (user2)
        self.client.login(username="testuser2", password="password123")

        # User2 mencoba mengakses detail -> 403 Forbidden & gunakan template 403.html
        res_detail = self.client.get(reverse("koleksi:detail", args=[tanaman_user1.id]))
        self.assertEqual(res_detail.status_code, 403)
        self.assertTemplateUsed(res_detail, "403.html")

        # User2 mencoba mengubah tanaman user1 -> 403 Forbidden
        res_update = self.client.post(reverse("koleksi:update", args=[tanaman_user1.id]), {
            "nama_panggilan": "Dibajak User2",
        })
        self.assertEqual(res_update.status_code, 403)

        # User2 mencoba menghapus tanaman user1 -> 403 Forbidden
        res_delete = self.client.post(reverse("koleksi:delete", args=[tanaman_user1.id]))
        self.assertEqual(res_delete.status_code, 403)

        # User2 mencoba menambahkan jurnal ke tanaman user1 -> 403 Forbidden
        res_jurnal = self.client.post(reverse("koleksi:add_journal", args=[tanaman_user1.id]), {
            "tanggal": "2026-10-28",
            "catatan": "Jurnal ilegal",
        })
        self.assertEqual(res_jurnal.status_code, 403)

        # 2. Pengguna anonim (belum login) juga harus diblokir (403 Forbidden)
        self.client.logout()

        res_anon_detail = self.client.get(reverse("koleksi:detail", args=[tanaman_user1.id]))
        self.assertEqual(res_anon_detail.status_code, 403)

        res_anon_update = self.client.post(reverse("koleksi:update", args=[tanaman_user1.id]), {
            "nama_panggilan": "Dibajak Anon",
        })
        self.assertEqual(res_anon_update.status_code, 403)

        res_anon_delete = self.client.post(reverse("koleksi:delete", args=[tanaman_user1.id]))
        self.assertEqual(res_anon_delete.status_code, 403)

    def test_security_rate_limiting(self):
        from django.core.cache import cache
        cache.clear()

        # Uji rate limiting pada endpoint create_tanaman
        for _ in range(20):
            res = self.client.get(reverse("koleksi:create_tanaman"))
            self.assertEqual(res.status_code, 200)

        # Request ke-21 harus ditolak dengan status 429 Too Many Requests
        res_blocked = self.client.get(reverse("koleksi:create_tanaman"))
        self.assertEqual(res_blocked.status_code, 429)
        self.assertIn("Terlalu banyak permintaan", res_blocked.content.decode())
        cache.clear()

    def test_forms_validation_and_xss_sanitization(self):
        # Valid TanamanForm
        form_valid = TanamanForm(data={"nama_panggilan": "Bonsai Ficus"})
        self.assertTrue(form_valid.is_valid())

        # Sanitasi XSS: strip HTML tags
        form_xss = TanamanForm(data={"nama_panggilan": "<b>Bonsai Super</b>", "catatan": "<script>alert(1)</script>Media baru"})
        self.assertTrue(form_xss.is_valid())
        self.assertEqual(form_xss.cleaned_data["nama_panggilan"], "Bonsai Super")
        self.assertEqual(form_xss.cleaned_data["catatan"], "alert(1)Media baru")

        # Invalid TanamanForm (nama_panggilan kosong atau hanya tag HTML)
        form_empty_html = TanamanForm(data={"nama_panggilan": "<b></b>"})
        self.assertFalse(form_empty_html.is_valid())
        self.assertIn("nama_panggilan", form_empty_html.errors)

        # Valid JurnalPertumbuhanForm
        form_jurnal = JurnalPertumbuhanForm(data={"tanggal": "2026-10-28", "catatan": "Disiram pagi hari"})
        self.assertTrue(form_jurnal.is_valid())

    def test_models_str_and_properties(self):
        tanaman = Tanaman.objects.create(
            nama_panggilan="Calathea Cantik",
            nama_ilmiah="Calathea orbifolia",
        )
        self.assertEqual(str(tanaman), "Calathea Cantik")
        self.assertEqual(tanaman.jumlah_jurnal, 0)

        jurnal = JurnalPertumbuhan.objects.create(
            tanaman=tanaman,
            tanggal=date(2026, 10, 28),
            catatan="Semprot daun",
        )
        self.assertIn("Jurnal Calathea Cantik", str(jurnal))
        self.assertEqual(tanaman.jumlah_jurnal, 1)

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
