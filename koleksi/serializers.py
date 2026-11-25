from django.utils.html import strip_tags
from rest_framework import serializers

from koleksi.models import JurnalPertumbuhan, Tanaman


class TanamanSerializer(serializers.ModelSerializer):
    """Serializer untuk data koleksi tanaman pribadi pengguna."""

    jumlah_jurnal = serializers.SerializerMethodField()

    class Meta:
        model = Tanaman
        fields = [
            "id",
            "spesies_id",
            "nama_panggilan",
            "nama_ilmiah",
            "lokasi",
            "tanggal_mulai",
            "cahaya",
            "penyiraman",
            "tingkat_kesulitan",
            "foto",
            "catatan",
            "jumlah_jurnal",
            "dibuat_pada",
            "diperbarui_pada",
        ]
        read_only_fields = ["id", "dibuat_pada", "diperbarui_pada"]

    def validate_nama_panggilan(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Nama panggilan tidak boleh kosong.")
        return value

    def validate_nama_ilmiah(self, value):
        return strip_tags(value).strip()

    def validate_lokasi(self, value):
        return strip_tags(value).strip()

    def validate_catatan(self, value):
        return strip_tags(value)

    def get_jumlah_jurnal(self, obj):
        return obj.jurnals.count()


class JurnalPertumbuhanSerializer(serializers.ModelSerializer):
    """Serializer untuk entri jurnal pertumbuhan suatu tanaman."""

    class Meta:
        model = JurnalPertumbuhan
        fields = [
            "id",
            "tanaman",
            "tanggal",
            "catatan",
            "foto",
            "dibuat_pada",
        ]
        read_only_fields = ["id", "tanaman", "dibuat_pada"]

    def validate_catatan(self, value):
        return strip_tags(value)
