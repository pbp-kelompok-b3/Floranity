"""Data contoh untuk melihat tampilan sebelum model dan API dipasang.

Nama field di sini sengaja sama dengan yang dipakai template, jadi saat model
sudah ada, view tinggal mengganti sumber datanya tanpa mengubah template.
"""

SPESIES = [
    {
        "id": 1,
        "nama_umum": "Monstera",
        "nama_ilmiah": "Monstera deliciosa",
        "famili": "Araceae",
        "cahaya": "Cahaya tidak langsung",
        "penyiraman": "Sedang",
        "tingkat_kesulitan": "Mudah",
        "siklus": "Tahunan",
        "dalam_ruangan": "Ya",
        "gambar": "",
        "deskripsi": (
            "Tanaman hias berdaun lebar dengan lubang khas. Tumbuh baik di ruangan "
            "terang tanpa sinar matahari langsung dan menyukai media yang porous."
        ),
    },
    {
        "id": 2,
        "nama_umum": "Lidah Mertua",
        "nama_ilmiah": "Sansevieria trifasciata",
        "famili": "Asparagaceae",
        "cahaya": "Terang sampai teduh",
        "penyiraman": "Jarang",
        "tingkat_kesulitan": "Sangat mudah",
        "siklus": "Tahunan",
        "dalam_ruangan": "Ya",
        "gambar": "",
        "deskripsi": "Tahan kekeringan dan cocok untuk pemula. Siram setelah media benar-benar kering.",
    },
    {
        "id": 3,
        "nama_umum": "Tomat",
        "nama_ilmiah": "Solanum lycopersicum",
        "famili": "Solanaceae",
        "cahaya": "Matahari penuh",
        "penyiraman": "Sering",
        "tingkat_kesulitan": "Sedang",
        "siklus": "Semusim",
        "dalam_ruangan": "Tidak",
        "gambar": "",
        "deskripsi": "Butuh sinar matahari penuh minimal enam jam sehari dan penyiraman teratur.",
    },
    {
        "id": 4,
        "nama_umum": "Basil",
        "nama_ilmiah": "Ocimum basilicum",
        "famili": "Lamiaceae",
        "cahaya": "Matahari penuh",
        "penyiraman": "Sedang",
        "tingkat_kesulitan": "Mudah",
        "siklus": "Semusim",
        "dalam_ruangan": "Ya",
        "gambar": "",
        "deskripsi": "Herba dapur yang cepat tumbuh. Pangkas pucuk agar tidak cepat berbunga.",
    },
    {
        "id": 5,
        "nama_umum": "Peace Lily",
        "nama_ilmiah": "Spathiphyllum wallisii",
        "famili": "Araceae",
        "cahaya": "Cahaya rendah",
        "penyiraman": "Sedang",
        "tingkat_kesulitan": "Mudah",
        "siklus": "Tahunan",
        "dalam_ruangan": "Ya",
        "gambar": "",
        "deskripsi": "Memberi tanda saat kurang air dengan daun yang layu, lalu pulih setelah disiram.",
    },
    {
        "id": 6,
        "nama_umum": "Kaktus Centong",
        "nama_ilmiah": "Opuntia ficus-indica",
        "famili": "Cactaceae",
        "cahaya": "Matahari penuh",
        "penyiraman": "Sangat jarang",
        "tingkat_kesulitan": "Mudah",
        "siklus": "Tahunan",
        "dalam_ruangan": "Tidak",
        "gambar": "",
        "deskripsi": "Sukulen tahan panas. Terlalu sering disiram membuat batangnya membusuk.",
    },
]

TANAMAN = [
    {
        "id": 1,
        "spesies_id": 1,
        "nama_panggilan": "Monstera meja belajar",
        "nama_ilmiah": "Monstera deliciosa",
        "lokasi": "Kamar, dekat jendela",
        "tanggal_mulai": "12 Maret 2026",
        "catatan": "Dapat dari teman, media tanam campuran sekam dan cocopeat.",
        "cahaya": "Cahaya tidak langsung",
        "penyiraman": "Sedang",
        "tingkat_kesulitan": "Mudah",
        "foto": "",
    },
    {
        "id": 2,
        "spesies_id": 4,
        "nama_panggilan": "Basil dapur",
        "nama_ilmiah": "Ocimum basilicum",
        "lokasi": "Dapur, ambang jendela",
        "tanggal_mulai": "2 Agustus 2026",
        "catatan": "Ditanam dari biji.",
        "cahaya": "Matahari penuh",
        "penyiraman": "Sedang",
        "tingkat_kesulitan": "Mudah",
        "foto": "",
    },
    {
        "id": 3,
        "spesies_id": 2,
        "nama_panggilan": "Lidah mertua ruang tamu",
        "nama_ilmiah": "Sansevieria trifasciata",
        "lokasi": "Ruang tamu",
        "tanggal_mulai": "20 Januari 2026",
        "catatan": "",
        "cahaya": "Terang sampai teduh",
        "penyiraman": "Jarang",
        "tingkat_kesulitan": "Sangat mudah",
        "foto": "",
    },
]

# Kode filter Perenual dipetakan ke teks data contoh, supaya dropdown di katalog
# bisa dicoba sebelum API disambungkan
KODE_AIR = {"frequent": "Sering", "average": "Sedang", "minimum": "Jarang", "none": "Sangat jarang"}
KODE_CAHAYA = {
    "full_sun": "Matahari penuh",
    "sun-part_shade": "Matahari sebagian",
    "part_shade": "Cahaya tidak langsung",
    "full_shade": "Cahaya rendah",
}


def cari_spesies(q="", air="", cahaya=""):
    """Meniru pencarian Perenual, dipakai selama view masih memakai data contoh."""
    hasil = SPESIES
    if q:
        q = q.lower()
        hasil = [
            s for s in hasil
            if q in s["nama_umum"].lower() or q in s["nama_ilmiah"].lower()
        ]
    if air in KODE_AIR:
        hasil = [s for s in hasil if s["penyiraman"] == KODE_AIR[air]]
    if cahaya in KODE_CAHAYA:
        hasil = [s for s in hasil if s["cahaya"] == KODE_CAHAYA[cahaya]]
    return hasil


def ambil_spesies(spesies_id):
    for s in SPESIES:
        if s["id"] == spesies_id:
            return s
    return None


def ambil_tanaman(tanaman_id):
    for t in TANAMAN:
        if t["id"] == tanaman_id:
            return t
    return None
