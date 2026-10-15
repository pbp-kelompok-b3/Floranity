"""View kerangka untuk Koleksi & Katalog Tanaman.

Semua data masih berasal dari sample_data.py supaya tampilan bisa dilihat lebih
dulu. Setiap tempat yang nanti diganti model atau panggilan Perenual sudah
ditandai dengan komentar TODO.
"""

from datetime import date
from urllib.parse import urlencode

from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from . import sample_data, services

JUMLAH_PER_HALAMAN = 6


# --------------------------------------------------------------------------
# Katalog (data referensi spesies dari Perenual)
# --------------------------------------------------------------------------

def katalog(request):
    """Daftar spesies dengan pencarian, filter, dan paginasi sederhana."""
    q = request.GET.get("q", "").strip()
    air = request.GET.get("air", "")
    cahaya = request.GET.get("cahaya", "")
    try:
        halaman = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        halaman = 1

    # TODO: ganti dengan services.cari_spesies(q, halaman, air, cahaya) yang
    # memanggil endpoint species-list Perenual.
    hasil = sample_data.cari_spesies(q, air=air, cahaya=cahaya)

    awal = (halaman - 1) * JUMLAH_PER_HALAMAN
    akhir = awal + JUMLAH_PER_HALAMAN

    return render(request, "koleksi/katalog_list.html", {
        "spesies_list": hasil[awal:akhir],
        "q": q,
        "air": air,
        "cahaya": cahaya,
        "pilihan_air": services.PILIHAN_AIR,
        "pilihan_cahaya": services.PILIHAN_CAHAYA,
        "halaman": halaman,
        "ada_halaman_berikut": len(hasil) > akhir,
        # Dipakai untuk menjaga filter tetap terpasang saat pindah halaman
        "query_filter": urlencode({"q": q, "air": air, "cahaya": cahaya}),
    })


def katalog_detail(request, spesies_id):
    """Detail satu spesies.

    Pada paket gratis Perenual, detail hanya tersedia untuk id <= 3000. Kalau
    terkunci, halaman tetap dibuka dengan data ringkas dan satu keterangan.
    """
    # TODO: ganti dengan services.ambil_spesies(spesies_id) yang memanggil
    # endpoint species/details Perenual.
    spesies = sample_data.ambil_spesies(spesies_id)
    if spesies is None:
        raise Http404("Spesies tidak ditemukan")

    return render(request, "koleksi/katalog_detail.html", {
        "spesies": spesies,
        "detail_terkunci": False,
    })


# --------------------------------------------------------------------------
# Koleksi pribadi (CRUD)
# --------------------------------------------------------------------------

# TODO: pasang @login_required di semua view koleksi setelah fitur auth siap.
def daftar(request):
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


def tambah(request):
    """Formulir tambah tanaman. Spesies bisa diisi otomatis dari katalog."""
    if request.method == "POST":
        # TODO: validasi lewat TanamanForm, simpan dengan pemilik=request.user.
        return redirect(f"{reverse('koleksi:daftar')}?pesan=Tanaman+berhasil+ditambahkan")

    awalan = {}
    spesies_id = request.GET.get("spesies_id")
    if spesies_id and spesies_id.isdigit():
        spesies = sample_data.ambil_spesies(int(spesies_id))
        if spesies:
            awalan = {
                "nama_ilmiah": spesies["nama_ilmiah"],
                "spesies_id": spesies["id"],
                "nama_panggilan": spesies["nama_umum"],
            }

    return render(request, "koleksi/koleksi_form.html", {
        "judul": "Tambah tanaman",
        "tanaman": awalan,
        "url_batal": reverse("koleksi:daftar"),
    })


def ubah(request, tanaman_id):
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


def hapus(request, tanaman_id):
    """Konfirmasi lalu hapus tanaman dari koleksi."""
    tanaman = sample_data.ambil_tanaman(tanaman_id)
    if tanaman is None:
        raise Http404("Tanaman tidak ditemukan")

    if request.method == "POST":
        # TODO: tanaman.delete()
        return redirect(f"{reverse('koleksi:daftar')}?pesan=Tanaman+berhasil+dihapus")

    return render(request, "koleksi/koleksi_hapus.html", {"tanaman": tanaman})


def jurnal_tambah(request, tanaman_id):
    """Menerima satu entri jurnal (foto dan catatan) dari halaman detail."""
    if request.method == "POST":
        # TODO: simpan lewat JurnalForm dengan tanaman_id sebagai foreign key.
        pass
    return redirect("koleksi:detail", tanaman_id=tanaman_id)
