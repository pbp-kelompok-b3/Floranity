from datetime import date
from .models import Tanaman, JurnalPertumbuhan


def seed_sample_data_if_empty():
    """Mengisi database dengan tanaman awal jika database masih kosong,

    sehingga aplikasi langsung memiliki data realistis.
    """
    if Tanaman.objects.exists():
        return

    t1 = Tanaman.objects.create(
        id=1,
        spesies_id=1,
        nama_panggilan="Monstera meja belajar",
        nama_ilmiah="Monstera deliciosa",
        lokasi="Meja belajar, dekat jendela timur",
        tanggal_mulai=date(2026, 3, 12),
        cahaya="Cahaya tidak langsung",
        penyiraman="Sedang",
        tingkat_kesulitan="Mudah",
        catatan="Disiram saat dua inci atas media kering. Lap daun dari debu setiap dua minggu.",
    )
    JurnalPertumbuhan.objects.create(
        tanaman=t1,
        tanggal=date(2026, 9, 28),
        catatan="Dua daun baru terbuka. Daun paling bawah mulai menguning, dipangkas.",
    )
    JurnalPertumbuhan.objects.create(
        tanaman=t1,
        tanggal=date(2026, 9, 5),
        catatan="Dipindah ke pot 25 cm, media diganti campuran baru.",
    )
    JurnalPertumbuhan.objects.create(
        tanaman=t1,
        tanggal=date(2026, 3, 12),
        catatan="Masuk koleksi, tinggi sekitar 30 cm dengan empat daun.",
    )

    t2 = Tanaman.objects.create(
        id=2,
        spesies_id=4,
        nama_panggilan="Basil dapur",
        nama_ilmiah="Ocimum basilicum",
        lokasi="Dapur, ambang jendela",
        tanggal_mulai=date(2026, 8, 2),
        cahaya="Matahari penuh",
        penyiraman="Sedang",
        tingkat_kesulitan="Mudah",
        catatan="Ditanam dari biji.",
    )
    JurnalPertumbuhan.objects.create(
        tanaman=t2,
        tanggal=date(2026, 10, 14),
        catatan="Panen pertama tiga tangkai untuk masak.",
    )

    Tanaman.objects.create(
        id=3,
        spesies_id=2,
        nama_panggilan="Lidah mertua ruang tamu",
        nama_ilmiah="Sansevieria trifasciata",
        lokasi="Ruang tamu",
        tanggal_mulai=date(2026, 1, 20),
        cahaya="Terang sampai teduh",
        penyiraman="Jarang",
        tingkat_kesulitan="Sangat mudah",
    )
