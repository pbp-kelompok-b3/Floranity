from django.urls import path

from . import views

app_name = "koleksi"

urlpatterns = [
    # Katalog spesies
    path("katalog/", views.katalog, name="katalog"),
    path("katalog/<int:spesies_id>/", views.katalog_detail, name="katalog_detail"),

    # Koleksi pribadi
    path("koleksi/", views.daftar, name="daftar"),
    path("koleksi/jurnal/", views.jurnal, name="jurnal"),
    path("koleksi/jurnal/tambah/", views.jurnal_tambah, name="jurnal_tambah"),
    path("koleksi/tambah/", views.tambah, name="tambah"),
    path("koleksi/<int:tanaman_id>/", views.detail, name="detail"),
    path("koleksi/<int:tanaman_id>/ubah/", views.ubah, name="ubah"),
    path("koleksi/<int:tanaman_id>/hapus/", views.hapus, name="hapus"),
]
