from functools import wraps
import time
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from .models import Tanaman


def is_ajax_or_json(request):
    """Mendeteksi apakah permintaan datang dari AJAX (fetch/xhr) atau mengharapkan format JSON."""
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or request.path.endswith("-ajax/")
    )


def plant_owner_required(view_func):
    """Custom security decorator: Memastikan pengguna hanya dapat mengakses
    atau memanipulasi data tanaman miliknya sendiri (Object-Level Access Control).

    Mencegah akses ilegal dari pengguna lain maupun pengguna anonim ke data pribadi.
    Memberikan respons 403 dengan UI error feedback yang jelas (403.html) untuk
    permintaan web biasa, atau format JSON untuk AJAX.
    """
    @wraps(view_func)
    def _wrapped_view(request, tanaman_id, *args, **kwargs):
        tanaman = get_object_or_404(Tanaman, id=tanaman_id)

        # Pengguna hanya boleh memanipulasi jika tanaman tidak berpemilik (sample data)
        # atau jika user adalah pemilik sah dari tanaman tersebut.
        if tanaman.pemilik and (not request.user.is_authenticated or tanaman.pemilik != request.user):
            pesan_error = "Anda tidak memiliki izin untuk mengakses atau memodifikasi data tanaman ini."
            if is_ajax_or_json(request):
                return JsonResponse({"message": pesan_error}, status=403)
            return render(
                request,
                "403.html",
                {
                    "pesan": pesan_error,
                    "tanaman": tanaman,
                },
                status=403,
            )

        return view_func(request, tanaman_id, *args, **kwargs)

    return _wrapped_view


def rate_limit_sensitive(max_requests=10, window_seconds=60, key_prefix="rate_limit"):
    """Custom security decorator: Membatasi frekuensi request pada endpoint sensitif
    (Rate Limiting) untuk mencegah serangan DoS, spamming form, atau brute-force.

    Menggunakan Django cache untuk mencatat riwayat timestamp request per identifier
    (user ID atau IP address client).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Identifikasi client: pakai user ID jika login, atau IP address jika anonim
            if request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            else:
                x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                if x_forwarded_for:
                    identifier = x_forwarded_for.split(",")[0].strip()
                else:
                    identifier = request.META.get("REMOTE_ADDR", "unknown")

            cache_key = f"{key_prefix}:{view_func.__name__}:{identifier}"
            sekarang = time.time()
            riwayat_request = cache.get(cache_key, [])

            # Filter request yang masih berada dalam rentang jendela waktu (window_seconds)
            riwayat_aktif = [t for t in riwayat_request if sekarang - t < window_seconds]

            if len(riwayat_aktif) >= max_requests:
                pesan = f"Terlalu banyak permintaan. Silakan tunggu beberapa saat sebelum mencoba lagi."
                if is_ajax_or_json(request):
                    return JsonResponse({"message": pesan}, status=429)
                return HttpResponse(pesan, status=429)

            # Catat waktu request baru ke dalam cache
            riwayat_aktif.append(sekarang)
            cache.set(cache_key, riwayat_aktif, timeout=window_seconds)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
