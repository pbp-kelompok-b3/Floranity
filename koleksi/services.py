"""Pemanggilan Perenual API. Hanya dua endpoint yang dipakai modul ini:

    GET /api/v2/species-list            daftar spesies untuk katalog (+ filter)
    GET /api/v2/species/details/<id>    detail satu spesies

Belum dipakai oleh views.py (views masih memakai sample_data.py). Cara
menghubungkannya ada di README.md bagian "Menyambung ke Perenual".

Kunci API dibaca dari settings.PERENUAL_API_KEY, yang sebaiknya diisi dari
environment variable, bukan ditulis langsung di settings.py.
"""

import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

BASE_URL = "https://perenual.com/api/v2"
CACHE_DETIK = 60 * 60  # Kuota paket gratis hanya 100 request per hari
TIMEOUT = 10

# Spesies dengan id di atas angka ini hanya tersedia untuk paket berbayar
BATAS_DETAIL_GRATIS = 3000

# Nilai filter yang diterima Perenual, dipakai juga untuk mengisi dropdown katalog
PILIHAN_AIR = [
    ("frequent", "Sering"),
    ("average", "Rata-rata"),
    ("minimum", "Sedikit"),
    ("none", "Tidak perlu"),
]

PILIHAN_CAHAYA = [
    ("full_sun", "Matahari Penuh"),
    ("sun-part_shade", "Matahari Sebagian"),
    ("part_shade", "Teduh Sebagian"),
    ("full_shade", "Teduh Penuh"),
]

PILIHAN_SIKLUS = [
    ("perennial", "Tahunan"),
    ("annual", "Semusim"),
    ("biennial", "Dua Musim"),
]

# Pemetaan terjemahan dari nilai bawaan berbahasa Inggris di API Perenual ke bahasa Indonesia
TERJEMAHAN_CAHAYA = {
    "full sun": "Matahari Penuh",
    "full_sun": "Matahari Penuh",
    "full-sun": "Matahari Penuh",
    "fullsun": "Matahari Penuh",
    "part sun": "Matahari Sebagian",
    "part_sun": "Matahari Sebagian",
    "partial sun": "Matahari Sebagian",
    "partial_sun": "Matahari Sebagian",
    "sun-part_shade": "Matahari Sebagian",
    "sun_part_shade": "Matahari Sebagian",
    "sun-part shade": "Matahari Sebagian",
    "sun and part shade": "Matahari Sebagian",
    "part shade": "Teduh Sebagian",
    "part_shade": "Teduh Sebagian",
    "partial shade": "Teduh Sebagian",
    "partial_shade": "Teduh Sebagian",
    "full shade": "Teduh Penuh",
    "full_shade": "Teduh Penuh",
    "filtered shade": "Cahaya Tersaring",
    "filtered_shade": "Cahaya Tersaring",
    "dappled shade": "Cahaya Tersaring",
    "deep shade": "Teduh Total",
    "bright indirect": "Cahaya Tidak Langsung",
    "bright indirect light": "Cahaya Tidak Langsung",
    "indirect": "Cahaya Tidak Langsung",
    "low light": "Cahaya Rendah",
    "shade": "Teduh",
}

TERJEMAHAN_AIR = {
    "average": "Rata-rata",
    "frequent": "Sering",
    "minimum": "Sedikit",
    "none": "Tidak Perlu",
    "low": "Sedikit",
    "medium": "Rata-rata",
    "high": "Sering",
    "moderate": "Sedang",
    "occasional": "Kadang-kadang",
    "rare": "Jarang",
    "rarely": "Jarang",
    "daily": "Setiap Hari",
    "weekly": "Mingguan",
}

TERJEMAHAN_KESULITAN = {
    "low": "Mudah",
    "easy": "Mudah",
    "very easy": "Sangat Mudah",
    "very_easy": "Sangat Mudah",
    "medium": "Sedang",
    "moderate": "Sedang",
    "high": "Sulit",
    "hard": "Sulit",
    "very hard": "Sangat Sulit",
    "very_hard": "Sangat Sulit",
}

TERJEMAHAN_SIKLUS = {
    "perennial": "Tahunan",
    "annual": "Semusim",
    "biennial": "Dua Musim",
    "biannual": "Dua Musim",
    "herbaceous perennial": "Tahunan Herba",
}


def _terjemahkan_satuan(nilai, kamus):
    if not nilai:
        return ""
    teks = str(nilai).strip()
    if not teks or "upgrade" in teks.lower():
        return ""

    kunci_lower = teks.lower()
    if kunci_lower in kamus:
        return kamus[kunci_lower]

    kunci_bersih = kunci_lower.replace("_", " ").replace("-", " ").strip()
    if kunci_bersih in kamus:
        return kamus[kunci_bersih]

    return teks


def _terjemahkan(nilai, kamus):
    """Menerjemahkan string atau list string dari respons Perenual ke bahasa Indonesia."""
    if not nilai:
        return ""
    if isinstance(nilai, list):
        hasil = []
        for item in nilai:
            t = _terjemahkan_satuan(item, kamus)
            if t and t not in hasil:
                hasil.append(t)
        return ", ".join(hasil)
    if isinstance(nilai, str):
        if "upgrade" in nilai.lower():
            return ""
        if "," in nilai:
            bagian = [b.strip() for b in nilai.split(",") if b.strip()]
            hasil = []
            for b in bagian:
                t = _terjemahkan_satuan(b, kamus)
                if t and t not in hasil:
                    hasil.append(t)
            return ", ".join(hasil)
        return _terjemahkan_satuan(nilai, kamus)
    return str(nilai)


def _dalam_ruangan(nilai):
    if isinstance(nilai, bool):
        return "Ya" if nilai else "Tidak"
    if isinstance(nilai, str):
        if nilai.lower() in ("true", "1", "yes", "ya"):
            return "Ya"
        if nilai.lower() in ("false", "0", "no", "tidak"):
            return "Tidak"
    return "Tidak" if not nilai else "Ya"


def _ambil_json(path, params):
    params["key"] = getattr(settings, "PERENUAL_API_KEY", "")
    url = f"{BASE_URL}/{path}?{urlencode(params)}"

    kunci_cache = f"perenual:{path}:{urlencode(sorted(params.items()))}"
    tersimpan = cache.get(kunci_cache)
    if tersimpan is not None:
        return tersimpan

    req = Request(url, headers={"User-Agent": "Floranity/1.0 (Mozilla/5.0)"})
    with urlopen(req, timeout=TIMEOUT) as respons:
        data = json.loads(respons.read().decode("utf-8"))

    cache.set(kunci_cache, data, CACHE_DETIK)
    return data


def _teks(nilai, bawaan=""):
    """Paket gratis mengganti sebagian field dengan ajakan upgrade, itu dibuang."""
    if isinstance(nilai, list):
        nilai = ", ".join(str(x) for x in nilai if x)
    if not isinstance(nilai, str) or "upgrade" in nilai.lower():
        return bawaan
    return nilai


def _gambar(default_image):
    if not isinstance(default_image, dict):
        return ""
    url = default_image.get("small_url") or default_image.get("thumbnail") or ""
    return "" if "upgrade_access" in url else url


def _bentuk_spesies(item):
    """Mengubah respons Perenual menjadi field yang dipakai template."""
    return {
        "id": item.get("id"),
        "nama_umum": _teks(item.get("common_name"), "Tanpa nama umum"),
        "nama_ilmiah": _teks(item.get("scientific_name")),
        "famili": _teks(item.get("family")),
        "cahaya": _terjemahkan(item.get("sunlight"), TERJEMAHAN_CAHAYA),
        "penyiraman": _terjemahkan(item.get("watering"), TERJEMAHAN_AIR),
        "tingkat_kesulitan": _terjemahkan(item.get("care_level"), TERJEMAHAN_KESULITAN),
        "siklus": _terjemahkan(item.get("cycle"), TERJEMAHAN_SIKLUS),
        "dalam_ruangan": _dalam_ruangan(item.get("indoor")),
        "deskripsi": _teks(item.get("description")),
        "gambar": _gambar(item.get("default_image")),
    }


def cari_spesies(q="", halaman=1, air="", cahaya="", siklus=""):
    """Daftar spesies dari endpoint species-list.

    Filter air, cahaya, dan siklus dikerjakan oleh server Perenual, jadi hasilnya
    tetap benar walaupun nilainya sendiri tidak ikut dikirim di paket gratis.
    """
    params = {"q": q, "page": halaman}
    if air:
        params["watering"] = air
    if cahaya:
        params["sunlight"] = cahaya
    if siklus:
        params["cycle"] = siklus

    data = _ambil_json("species-list", params)
    return [_bentuk_spesies(item) for item in data.get("data", [])]


def ambil_spesies(spesies_id):
    """Detail satu spesies dari endpoint species/details.

    Mengembalikan None kalau detailnya terkunci, yaitu untuk id di atas
    BATAS_DETAIL_GRATIS yang dibalas Perenual dengan 429. Pemanggil menyiapkan
    jalur cadangan, misalnya memakai data ringkas dari hasil pencarian.
    """
    if spesies_id > BATAS_DETAIL_GRATIS:
        return None
    try:
        data = _ambil_json(f"species/details/{spesies_id}", {})
    except HTTPError as err:
        if err.code == 429:
            return None
        raise
    return _bentuk_spesies(data)
