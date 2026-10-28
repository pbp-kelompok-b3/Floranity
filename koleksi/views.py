"""View kerangka untuk Koleksi & Katalog Tanaman.

Semua data masih berasal dari sample_data.py supaya tampilan bisa dilihat lebih
dulu. Setiap tempat yang nanti diganti model atau panggilan Perenual sudah
ditandai dengan komentar TODO.
"""

from datetime import date
from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from . import sample_data, services

JUMLAH_PER_HALAMAN = 6


# --------------------------------------------------------------------------
# Katalog (data referensi spesies dari Perenual)
# --------------------------------------------------------------------------

def catalog(request):
    """Daftar spesies dengan pencarian, filter, dan paginasi sederhana."""
    q = request.GET.get("q", "").strip()
    air = request.GET.get("air", "")
    cahaya = request.GET.get("cahaya", "")
    try:
        halaman = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        halaman = 1

    spesies_list = []
    ada_berikut = False

    if getattr(settings, "PERENUAL_API_KEY", ""):
        try:
            spesies_list = services.cari_spesies(q=q, halaman=halaman, air=air, cahaya=cahaya)
            ada_berikut = len(spesies_list) >= JUMLAH_PER_HALAMAN
        except Exception:
            spesies_list = []

    if not spesies_list and not (getattr(settings, "PERENUAL_API_KEY", "") and q):
        hasil = sample_data.cari_spesies(q, air=air, cahaya=cahaya)
        awal = (halaman - 1) * JUMLAH_PER_HALAMAN
        akhir = awal + JUMLAH_PER_HALAMAN
        spesies_list = hasil[awal:akhir]
        ada_berikut = len(hasil) > akhir

    return render(request, "koleksi/katalog_list.html", {
        "spesies_list": spesies_list,
        "q": q,
        "air": air,
        "cahaya": cahaya,
        "pilihan_air": services.PILIHAN_AIR,
        "pilihan_cahaya": services.PILIHAN_CAHAYA,
        "halaman": halaman,
        "ada_halaman_berikut": ada_berikut,
        # Dipakai untuk menjaga filter tetap terpasang saat pindah halaman
        "query_filter": urlencode({"q": q, "air": air, "cahaya": cahaya}),
    })


def catalog_detail(request, spesies_id):
    """Detail satu spesies.

    Pada paket gratis Perenual, detail hanya tersedia untuk id <= 3000. Kalau
    terkunci, halaman tetap dibuka dengan data ringkas dan satu keterangan.
    """
    spesies = None
    detail_terkunci = False

    if getattr(settings, "PERENUAL_API_KEY", ""):
        try:
            spesies = services.ambil_spesies(spesies_id)
            if spesies is None and spesies_id > services.BATAS_DETAIL_GRATIS:
                detail_terkunci = True
        except Exception:
            pass

    if spesies is None:
        spesies = sample_data.ambil_spesies(spesies_id)

    if spesies is None:
        raise Http404("Spesies tidak ditemukan")

    return render(request, "koleksi/katalog_detail.html", {
        "spesies": spesies,
        "detail_terkunci": detail_terkunci,
    })


# --------------------------------------------------------------------------
# Koleksi pribadi (CRUD)
# --------------------------------------------------------------------------

# TODO: pasang @login_required di semua view koleksi setelah fitur auth siap.
def collection_list(request):
    """Koleksi milik pengguna yang sedang login."""
    q = request.GET.get("q", "").strip().lower()
    urut = request.GET.get("urut", "terbaru")

    # TODO: ganti dengan Tanaman.objects.filter(pemilik=request.user)
    tanaman_list = list(sample_data.TANAMAN)
    total = len(tanaman_list)

    if q:
        tanaman_list = [
            t for t in tanaman_list
            if q in t["nama_panggilan"].lower() or q in t["nama_ilmiah"].lower()
        ]
    if urut == "nama":
        tanaman_list.sort(key=lambda t: t["nama_panggilan"].lower())

    return render(request, "koleksi/koleksi_list.html", {
        "tanaman_list": tanaman_list,
        "total": total,
        "q": request.GET.get("q", ""),
        "urut": urut,
        "pesan": request.GET.get("pesan", ""),
    })


def detail(request, tanaman_id):
    """Detail satu tanaman beserta jurnal pertumbuhannya."""
    tanaman = sample_data.ambil_tanaman(tanaman_id)
    if tanaman is None:
        raise Http404("Tanaman tidak ditemukan")

    # TODO: pastikan tanaman.pemilik == request.user, kalau bukan kembalikan 404.
    return render(request, "koleksi/koleksi_detail.html", {
        "tanaman": tanaman,
        "jurnal_list": sample_data.JURNAL.get(tanaman_id, []),
        "hari_ini": date.today().isoformat(),
    })


def create(request):
    """Formulir tambah tanaman. Spesies bisa diisi otomatis dari katalog."""
    if request.method == "POST":
        # TODO: validasi lewat TanamanForm, simpan dengan pemilik=request.user.
        return redirect(f"{reverse('koleksi:collection_list')}?pesan=Tanaman+berhasil+ditambahkan")

    awalan = {}
    spesies_id = request.GET.get("spesies_id")
    if spesies_id and spesies_id.isdigit():
        spesies = None
        sid = int(spesies_id)
        if getattr(settings, "PERENUAL_API_KEY", ""):
            try:
                spesies = services.ambil_spesies(sid)
            except Exception:
                pass
        if not spesies:
            spesies = sample_data.ambil_spesies(sid)
        if spesies:
            awalan = {
                "nama_ilmiah": spesies["nama_ilmiah"],
                "spesies_id": spesies["id"],
                "nama_panggilan": spesies["nama_umum"],
            }

    return render(request, "koleksi/koleksi_form.html", {
        "judul": "Tambah tanaman",
        "tanaman": awalan,
        "url_batal": reverse("koleksi:collection_list"),
    })


def update(request, tanaman_id):
    """Formulir ubah info tanaman."""
    tanaman = sample_data.ambil_tanaman(tanaman_id)
    if tanaman is None:
        raise Http404("Tanaman tidak ditemukan")

    if request.method == "POST":
        # TODO: simpan perubahan lewat TanamanForm(instance=tanaman).
        return redirect("koleksi:detail", tanaman_id=tanaman_id)

    return render(request, "koleksi/koleksi_form.html", {
        "judul": "Ubah info tanaman",
        "tanaman": tanaman,
        "url_batal": reverse("koleksi:detail", args=[tanaman_id]),
    })


def delete(request, tanaman_id):
    """Konfirmasi lalu hapus tanaman dari koleksi."""
    tanaman = sample_data.ambil_tanaman(tanaman_id)
    if tanaman is None:
        raise Http404("Tanaman tidak ditemukan")

    if request.method == "POST":
        # TODO: tanaman.delete()
        return redirect(f"{reverse('koleksi:collection_list')}?pesan=Tanaman+berhasil+dihapus")

    return render(request, "koleksi/koleksi_hapus.html", {"tanaman": tanaman})


def add_journal(request, tanaman_id):
    """Menerima satu entri jurnal (foto dan catatan) dari halaman detail."""
    if request.method == "POST":
        # TODO: simpan lewat JurnalForm dengan tanaman_id sebagai foreign key.
        pass
    return redirect("koleksi:detail", tanaman_id=tanaman_id)


# Alias untuk kompatibilitas ke belakang
katalog = catalog
katalog_detail = catalog_detail
daftar = collection_list
tambah = create
ubah = update
hapus = delete
jurnal_tambah = add_journal
