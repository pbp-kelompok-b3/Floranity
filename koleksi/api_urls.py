from django.urls import path

from koleksi import api_views

app_name = "koleksi_api"

urlpatterns = [
    path("katalog/", api_views.katalog_list, name="katalog-list"),
    path("katalog/<int:spesies_id>/", api_views.katalog_detail, name="katalog-detail"),
    path("koleksi/", api_views.tanaman_list, name="tanaman-list"),
    path("koleksi/<int:tanaman_id>/", api_views.tanaman_detail, name="tanaman-detail"),
    path(
        "koleksi/<int:tanaman_id>/jurnal/",
        api_views.jurnal_list,
        name="jurnal-list",
    ),
]
