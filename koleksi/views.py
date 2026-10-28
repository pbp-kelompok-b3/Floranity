"""Views untuk modul Koleksi & Katalog Tanaman (Arsitektur MVT Penuh).

Menangani katalog referensi spesies (Perenual API) dan operasi CRUD database
untuk koleksi pribadi pengguna beserta jurnal pertumbuhannya.
"""

from datetime import date
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import JurnalPertumbuhanForm, TanamanForm
from .models import JurnalPertumbuhan, Tanaman
from .seed import seed_sample_data_if_empty
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

    context = {
        "spesies_list": spesies_list,
        "q": q,
        "air": air,
        "cahaya": cahaya,
        "pilihan_air": services.PILIHAN_AIR,
        "pilihan_cahaya": services.PILIHAN_CAHAYA,
        "halaman": halaman,
        "ada_halaman_berikut": ada_berikut,
        "query_filter": urlencode({"q": q, "air": air, "cahaya": cahaya}),
    }
    return render(request, "koleksi/katalog_list.html", context)


def catalog_detail(request, spesies_id):
    """Detail satu spesies dari katalog Perenual."""
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

    context = {
        "spesies": spesies,
        "detail_terkunci": detail_terkunci,
    }
    return render(request, "koleksi/katalog_detail.html", context)


# --------------------------------------------------------------------------
# Koleksi pribadi (CRUD Database via Django ORM & ModelForm)
# --------------------------------------------------------------------------

def show_collection(request):
    """Menampilkan daftar tanaman dalam koleksi pengguna dari database."""
    seed_sample_data_if_empty()

    if request.user.is_authenticated:
        qs = Tanaman.objects.filter(pemilik=request.user)
    else:
        qs = Tanaman.objects.all()

    q = request.GET.get("q", "").strip()
    urut = request.GET.get("urut", "terbaru")

    if q:
        qs = qs.filter(
            Q(nama_panggilan__icontains=q) |
            Q(nama_ilmiah__icontains=q)
        )

    if urut == "nama":
        qs = qs.order_by("nama_panggilan")
    elif urut == "lama":
        qs = qs.order_by("tanggal_mulai", "dibuat_pada")
    else:
        qs = qs.order_by("-dibuat_pada")

    context = {
        "tanaman_list": qs,
        "total": qs.count(),
        "q": q,
        "urut": urut,
    }
    return render(request, "koleksi/koleksi_list.html", context)


def detail(request, tanaman_id):
    """Detail satu tanaman dari database beserta seluruh catatan jurnal pertumbuhannya."""
    seed_sample_data_if_empty()
    tanaman = get_object_or_404(Tanaman, id=tanaman_id)

    context = {
        "tanaman": tanaman,
        "jurnal_list": tanaman.jurnals.all(),
        "hari_ini": date.today().isoformat(),
    }
    return render(request, "koleksi/koleksi_detail.html", context)


def create_tanaman(request):
    """Formulir penambahan tanaman baru ke dalam database."""
    post_data = None
    if request.method == "POST":
        post_data = request.POST.copy()
        if "spesies" in post_data and not post_data.get("nama_ilmiah"):
            post_data["nama_ilmiah"] = post_data["spesies"]

    form = TanamanForm(post_data or None)

    if request.method == "POST" and form.is_valid():
        tanaman = form.save(commit=False)
        if request.user.is_authenticated:
            tanaman.pemilik = request.user

        # Mengisi otomatis panduan perawatan dari katalog jika spesies_id terlampir
        if tanaman.spesies_id and (not tanaman.cahaya or not tanaman.penyiraman):
            try:
                spesies = services.ambil_spesies(tanaman.spesies_id) or sample_data.ambil_spesies(tanaman.spesies_id)
                if spesies:
                    if not tanaman.cahaya:
                        tanaman.cahaya = spesies.get("cahaya", "")
                    if not tanaman.penyiraman:
                        tanaman.penyiraman = spesies.get("penyiraman", "")
                    if not tanaman.tingkat_kesulitan:
                        tanaman.tingkat_kesulitan = spesies.get("tingkat_kesulitan", "")
                    if not tanaman.foto and spesies.get("gambar"):
                        tanaman.foto = spesies.get("gambar", "")
            except Exception:
                pass

        tanaman.save()
        messages.success(request, "Tanaman baru berhasil ditambahkan!")
        return redirect("koleksi:show_collection")

    awalan = {}
    spesies_id = request.GET.get("spesies_id")
    if spesies_id and spesies_id.isdigit():
        sid = int(spesies_id)
        spesies = None
        if getattr(settings, "PERENUAL_API_KEY", ""):
            try:
                spesies = services.ambil_spesies(sid)
            except Exception:
                pass
        if not spesies:
            spesies = sample_data.ambil_spesies(sid)
        if spesies:
            awalan = {
                "nama_ilmiah": spesies.get("nama_ilmiah", ""),
                "spesies_id": spesies.get("id"),
                "nama_panggilan": spesies.get("nama_umum", ""),
                "cahaya": spesies.get("cahaya", ""),
                "penyiraman": spesies.get("penyiraman", ""),
                "tingkat_kesulitan": spesies.get("tingkat_kesulitan", ""),
                "foto": spesies.get("gambar", ""),
            }

    context = {
        "judul": "Tambah tanaman",
        "tanaman": awalan,
        "form": form,
        "url_batal": reverse("koleksi:show_collection"),
    }
    return render(request, "koleksi/koleksi_form.html", context)


def update(request, tanaman_id):
    """Formulir pembaruan data tanaman di database."""
    tanaman = get_object_or_404(Tanaman, id=tanaman_id)

    post_data = None
    if request.method == "POST":
        post_data = request.POST.copy()
        if "spesies" in post_data and not post_data.get("nama_ilmiah"):
            post_data["nama_ilmiah"] = post_data["spesies"]

    form = TanamanForm(post_data or None, instance=tanaman)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Info tanaman berhasil diperbarui!")
        return redirect("koleksi:detail", tanaman_id=tanaman_id)

    context = {
        "judul": "Ubah info tanaman",
        "tanaman": tanaman,
        "form": form,
        "url_batal": reverse("koleksi:detail", args=[tanaman_id]),
    }
    return render(request, "koleksi/koleksi_form.html", context)


def delete(request, tanaman_id):
    """Konfirmasi dan penghapusan data tanaman dari database."""
    tanaman = get_object_or_404(Tanaman, id=tanaman_id)

    if request.method == "POST":
        tanaman.delete()
        messages.success(request, "Tanaman berhasil dihapus dari koleksi!")
        return redirect("koleksi:show_collection")

    context = {
        "tanaman": tanaman,
    }
    return render(request, "koleksi/koleksi_hapus.html", context)


def add_journal(request, tanaman_id):
    """Menyimpan entri jurnal pertumbuhan ke dalam database untuk tanaman yang ditentukan."""
    tanaman = get_object_or_404(Tanaman, id=tanaman_id)

    if request.method == "POST":
        form = JurnalPertumbuhanForm(request.POST)
        if form.is_valid():
            jurnal = form.save(commit=False)
            jurnal.tanaman = tanaman
            jurnal.save()
            messages.success(request, "Catatan jurnal berhasil ditambahkan!")

    return redirect("koleksi:detail", tanaman_id=tanaman_id)
