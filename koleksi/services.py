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
from urllib.request import urlopen

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
    ("average", "Sedang"),
    ("minimum", "Sedikit"),
    ("none", "Tidak perlu"),
]

PILIHAN_CAHAYA = [
    ("full_sun", "Matahari penuh"),
    ("sun-part_shade", "Matahari sebagian"),
    ("part_shade", "Teduh sebagian"),
    ("full_shade", "Teduh penuh"),
]

PILIHAN_SIKLUS = [
    ("perennial", "Tahunan"),
    ("annual", "Semusim"),
    ("biennial", "Dua musim"),
]


def _ambil_json(path, params):
    params["key"] = getattr(settings, "PERENUAL_API_KEY", "")
    url = f"{BASE_URL}/{path}?{urlencode(params)}"

    kunci_cache = f"perenual:{path}:{urlencode(sorted(params.items()))}"
    tersimpan = cache.get(kunci_cache)
    if tersimpan is not None:
        return tersimpan

    with urlopen(url, timeout=TIMEOUT) as respons:
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
        "cahaya": _teks(item.get("sunlight")),
        "penyiraman": _teks(item.get("watering")),
        "tingkat_kesulitan": _teks(item.get("care_level")),
        "siklus": _teks(item.get("cycle")),
        "dalam_ruangan": "Ya" if item.get("indoor") else "Tidak",
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
