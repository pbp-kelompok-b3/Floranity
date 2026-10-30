from django.contrib import admin
from .models import Tanaman


@admin.register(Tanaman)
class TanamanAdmin(admin.ModelAdmin):
    list_display = ("nama_panggilan", "nama_ilmiah", "pemilik", "lokasi", "tanggal_mulai", "dibuat_pada")
    list_filter = ("pemilik", "cahaya", "penyiraman", "tingkat_kesulitan")
    search_fields = ("nama_panggilan", "nama_ilmiah", "lokasi")
