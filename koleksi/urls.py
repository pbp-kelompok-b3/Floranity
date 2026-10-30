from django.urls import path
from koleksi.views import (
    catalog,
    catalog_detail,
    show_collection,
    create_tanaman,
    detail,
    update,
    delete,
    add_journal,
    jurnal,
    jurnal_tambah,
)

app_name = "koleksi"

urlpatterns = [
    # Katalog spesies
    path("katalog/", catalog, name="catalog"),
    path("katalog/<int:spesies_id>/", catalog_detail, name="catalog_detail"),

    # Koleksi pribadi
    path("koleksi/", show_collection, name="show_collection"),
    path("koleksi/jurnal/", jurnal, name="jurnal"),
    path("koleksi/jurnal/tambah/", jurnal_tambah, name="jurnal_tambah"),
    # Journal entries tied to the legacy plant detail form.
    path("koleksi/<int:tanaman_id>/jurnal/tambah/", add_journal, name="add_journal"),
    path("koleksi/tambah/", create_tanaman, name="create_tanaman"),
    path("koleksi/<int:tanaman_id>/", detail, name="detail"),
    path("koleksi/<int:tanaman_id>/ubah/", update, name="update"),
    path("koleksi/<int:tanaman_id>/hapus/", delete, name="delete"),
]
