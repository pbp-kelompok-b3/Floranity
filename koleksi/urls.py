from django.urls import path

from . import views

app_name = "koleksi"

urlpatterns = [
    # Katalog spesies
    path("katalog/", views.catalog, name="catalog"),
    path("katalog/<int:spesies_id>/", views.catalog_detail, name="catalog_detail"),

    # Koleksi pribadi
    path("koleksi/", views.collection_list, name="collection_list"),
    path("koleksi/tambah/", views.create, name="create"),
    path("koleksi/<int:tanaman_id>/", views.detail, name="detail"),
    path("koleksi/<int:tanaman_id>/ubah/", views.update, name="update"),
    path("koleksi/<int:tanaman_id>/hapus/", views.delete, name="delete"),
    path("koleksi/<int:tanaman_id>/jurnal/tambah/", views.add_journal, name="add_journal"),

    # Alias nama rute untuk kompatibilitas
    path("katalog/", views.catalog, name="katalog"),
    path("katalog/<int:spesies_id>/", views.catalog_detail, name="katalog_detail"),
    path("koleksi/", views.collection_list, name="daftar"),
    path("koleksi/tambah/", views.create, name="tambah"),
    path("koleksi/<int:tanaman_id>/ubah/", views.update, name="ubah"),
    path("koleksi/<int:tanaman_id>/hapus/", views.delete, name="hapus"),
    path("koleksi/<int:tanaman_id>/jurnal/tambah/", views.add_journal, name="jurnal_tambah"),
]
