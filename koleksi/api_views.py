from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from koleksi import sample_data, services
from koleksi.models import Tanaman
from koleksi.permissions import IsPlantOwner
from koleksi.serializers import JurnalPertumbuhanSerializer, TanamanSerializer

JUMLAH_PER_HALAMAN = 6


@api_view(["GET", "HEAD"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def katalog_list(request):
    """Mengembalikan daftar spesies katalog dengan pencarian dan filter."""
    q = request.query_params.get("q", "").strip()
    air = request.query_params.get("air", "").strip()
    cahaya = request.query_params.get("cahaya", "").strip()
    try:
        halaman = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        halaman = 1

    spesies_list = []
    ada_berikut = False
    api_error = False

    if getattr(settings, "PERENUAL_API_KEY", ""):
        try:
            spesies_list = services.cari_spesies(
                q=q, halaman=halaman, air=air, cahaya=cahaya
            )
            ada_berikut = len(spesies_list) >= JUMLAH_PER_HALAMAN
        except Exception:
            spesies_list = []
            api_error = True

    if not spesies_list and not (getattr(settings, "PERENUAL_API_KEY", "") and q):
        hasil = sample_data.cari_spesies(q, air=air, cahaya=cahaya)
        awal = (halaman - 1) * JUMLAH_PER_HALAMAN
        akhir = awal + JUMLAH_PER_HALAMAN
        spesies_list = hasil[awal:akhir]
        ada_berikut = len(hasil) > akhir

    return Response(
        {
            "halaman": halaman,
            "ada_halaman_berikut": ada_berikut,
            "api_error": api_error and bool(q),
            "results": spesies_list,
        }
    )


@api_view(["GET", "HEAD"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def katalog_detail(request, spesies_id):
    """Mengembalikan detail satu spesies dari katalog."""
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
        return Response(
            {"detail": "Spesies tidak ditemukan."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "detail_terkunci": detail_terkunci,
            "spesies": spesies,
        }
    )


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPlantOwner])
def tanaman_list(request):
    """Daftar koleksi tanaman milik pengguna login dan tambah tanaman baru."""
    if request.method in ("GET", "HEAD"):
        tanaman_qs = Tanaman.objects.filter(pemilik=request.user).prefetch_related(
            "jurnals"
        )
        q = request.query_params.get("q", "").strip()
        if q:
            tanaman_qs = tanaman_qs.filter(
                Q(nama_panggilan__icontains=q)
                | Q(nama_ilmiah__icontains=q)
                | Q(lokasi__icontains=q)
            )
        serializer = TanamanSerializer(tanaman_qs, many=True)
        return Response(serializer.data)

    serializer = TanamanSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(pemilik=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPlantOwner])
def tanaman_detail(request, tanaman_id):
    """Detail, ubah, dan hapus satu tanaman koleksi milik pengguna login."""
    tanaman = get_object_or_404(
        Tanaman.objects.prefetch_related("jurnals"), pk=tanaman_id
    )
    if tanaman.pemilik_id != request.user.id:
        return Response(
            {"detail": IsPlantOwner.message},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method in ("GET", "HEAD"):
        serializer = TanamanSerializer(tanaman)
        return Response(serializer.data)

    if request.method == "DELETE":
        tanaman.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = TanamanSerializer(
        tanaman,
        data=request.data,
        partial=request.method == "PATCH",
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPlantOwner])
def jurnal_list(request, tanaman_id):
    """Daftar dan tambah entri jurnal pertumbuhan untuk satu tanaman."""
    tanaman = get_object_or_404(Tanaman, pk=tanaman_id)
    if tanaman.pemilik_id != request.user.id:
        return Response(
            {"detail": IsPlantOwner.message},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method in ("GET", "HEAD"):
        jurnals = tanaman.jurnals.all()
        serializer = JurnalPertumbuhanSerializer(jurnals, many=True)
        return Response(serializer.data)

    serializer = JurnalPertumbuhanSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(tanaman=tanaman)
    return Response(serializer.data, status=status.HTTP_201_CREATED)
