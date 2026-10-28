"""View kerangka untuk Koleksi & Katalog Tanaman.

Semua data masih berasal dari sample_data.py supaya tampilan bisa dilihat lebih
dulu. Setiap tempat yang nanti diganti model atau panggilan Perenual sudah
ditandai dengan komentar TODO.
"""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from journal.forms import JournalLogForm
from journal.models import JournalLog

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

    spesies_list = []
    ada_berikut = False

    if settings.PRODUCTION and getattr(settings, "PERENUAL_API_KEY", ""):
        try:
            spesies_list = services.cari_spesies(q=q, halaman=halaman, air=air, cahaya=cahaya)
            ada_berikut = len(spesies_list) >= JUMLAH_PER_HALAMAN
        except Exception:
            spesies_list = []

    if not spesies_list and not (
        settings.PRODUCTION and getattr(settings, "PERENUAL_API_KEY", "") and q
    ):
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


def katalog_detail(request, spesies_id):
    """Detail satu spesies.

    Pada paket gratis Perenual, detail hanya tersedia untuk id <= 3000. Kalau
    terkunci, halaman tetap dibuka dengan data ringkas dan satu keterangan.
    """
    spesies = None
    detail_terkunci = False

    if settings.PRODUCTION and getattr(settings, "PERENUAL_API_KEY", ""):
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

# TODO(OAuth): apply Django's @login_required to private collection and journal
# views after OAuth login is merged; OAuth should authenticate into request.user.
def daftar(request):
    """Koleksi milik pengguna yang sedang login."""
    q = request.GET.get("q", "").strip().lower()
    urut = request.GET.get("urut", "terbaru")

    # TODO: ganti dengan Tanaman.objects.filter(pemilik=request.user)
    tanaman_list = [dict(tanaman) for tanaman in sample_data.TANAMAN]
    if request.user.is_authenticated:
        for tanaman in tanaman_list:
            tanaman["jumlah_jurnal"] = JournalLog.objects.filter(
                owner=request.user,
                plant_name__iexact=tanaman["nama_panggilan"],
                plant_species__iexact=tanaman["nama_ilmiah"],
            ).count()
    else:
        for tanaman in tanaman_list:
            tanaman["jumlah_jurnal"] = 0
    if q:
        tanaman_list = [
            t for t in tanaman_list
            if q in t["nama_panggilan"].lower() or q in t["nama_ilmiah"].lower()
        ]
    if urut == "nama":
        tanaman_list.sort(key=lambda t: t["nama_panggilan"].lower())

    return render(request, "koleksi/koleksi_list.html", {
        "tanaman_list": tanaman_list,
        "total": len(tanaman_list),
        "q": request.GET.get("q", ""),
        "urut": urut,
        "pesan": request.GET.get("pesan", ""),
    })


def jurnal(request):
    """Show the current user's journal entries, newest first."""
    jurnal_list = JournalLog.objects.none()
    if request.user.is_authenticated:
        jurnal_list = JournalLog.objects.filter(owner=request.user).order_by(
            "-occurred_at", "-created_at",
        )

    return render(request, "koleksi/journal_list.html", {
        "jurnal_list": jurnal_list,
    })


def jurnal_tambah(request):
    """Create a journal entry, optionally linked to a sample collection plant."""
    plant_id = request.POST.get("plant_id") or request.GET.get("plant_id", "")
    plant = (
        sample_data.ambil_tanaman(int(plant_id))
        if plant_id.isdigit()
        else None
    )
    initial = {
        "plant_name": request.GET.get("plant_name", ""),
        "plant_species": request.GET.get("plant_species", ""),
        "plant_type": request.GET.get("plant_type", ""),
    }
    if plant:
        initial.update({
            "plant_name": plant["nama_panggilan"],
            "plant_species": plant["nama_ilmiah"],
        })

    if request.method == "POST":
        form = JournalLogForm(request.POST, request.FILES, initial=initial)
        if plant:
            form.fields["plant_name"].disabled = True
            form.fields["plant_species"].disabled = True
        if form.is_valid():
            # TODO(OAuth): Require Django-authenticated users after the OAuth login
            if request.user.is_authenticated:
                form.save_for_owner(request.user)
                messages.success(request, "Catatan jurnal berhasil disimpan.")
                if plant:
                    return redirect("koleksi:detail", tanaman_id=int(plant_id))
                return redirect("koleksi:jurnal")
            form.add_error(None, "Masuk terlebih dahulu untuk menyimpan catatan jurnal.")
    else:
        form = JournalLogForm(initial=initial)
        if plant:
            form.fields["plant_name"].disabled = True
            form.fields["plant_species"].disabled = True

    return render(request, "journal/journal_log_form.html", {
        "form": form,
        "plant_id": int(plant_id) if plant else "",
        "url_batal": (
            reverse("koleksi:detail", kwargs={"tanaman_id": int(plant_id)})
            if plant else reverse("koleksi:jurnal")
        ),
    })


def detail(request, tanaman_id):
    """Detail one plant and its newest journal entries."""
    tanaman = sample_data.ambil_tanaman(tanaman_id)
    if tanaman is None:
        raise Http404("Tanaman tidak ditemukan")

    jurnal_list = JournalLog.objects.none()
    if request.user.is_authenticated:
        jurnal_list = JournalLog.objects.filter(
            owner=request.user,
            plant_name__iexact=tanaman["nama_panggilan"],
            plant_species__iexact=tanaman["nama_ilmiah"],
        ).order_by("-occurred_at", "-created_at")

    return render(request, "koleksi/koleksi_detail.html", {
        "tanaman": tanaman,
        "jurnal_list": jurnal_list,
        "journal_create_url": reverse("koleksi:jurnal_tambah") + "?" + urlencode({
            "plant_id": tanaman["id"],
            "plant_name": tanaman["nama_panggilan"],
            "plant_species": tanaman["nama_ilmiah"],
        }),
    })


def tambah(request):
    """Formulir tambah tanaman. Spesies bisa diisi otomatis dari katalog."""
    if request.method == "POST":
        # TODO: validasi lewat TanamanForm, simpan dengan pemilik=request.user.
        return redirect(f"{reverse('koleksi:daftar')}?pesan=Tanaman+berhasil+ditambahkan")

    awalan = {}
    spesies_id = request.GET.get("spesies_id")
    if spesies_id and spesies_id.isdigit():
        spesies = None
        sid = int(spesies_id)
        if settings.PRODUCTION and getattr(settings, "PERENUAL_API_KEY", ""):
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
