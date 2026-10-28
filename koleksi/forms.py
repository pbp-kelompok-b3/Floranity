from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from .models import Tanaman, JurnalPertumbuhan


class TanamanForm(forms.ModelForm):
    """Form untuk membuat dan memperbarui data Tanaman."""

    class Meta:
        model = Tanaman
        fields = [
            "nama_panggilan",
            "nama_ilmiah",
            "spesies_id",
            "lokasi",
            "tanggal_mulai",
            "cahaya",
            "penyiraman",
            "tingkat_kesulitan",
            "foto",
            "catatan",
        ]
        widgets = {
            "nama_panggilan": forms.TextInput(attrs={
                "id": "nama_panggilan",
                "placeholder": "Misalnya: Monstera meja belajar",
                "required": True,
            }),
            "nama_ilmiah": forms.TextInput(attrs={
                "id": "spesies",
                "placeholder": "Pilih dari katalog atau tulis sendiri",
            }),
            "spesies_id": forms.HiddenInput(),
            "lokasi": forms.TextInput(attrs={
                "id": "lokasi",
                "placeholder": "Misalnya: balkon, teras depan, meja kerja",
            }),
            "tanggal_mulai": forms.DateInput(attrs={
                "id": "tanggal_mulai",
                "type": "date",
            }),
            "catatan": forms.Textarea(attrs={
                "id": "catatan",
                "placeholder": "Catatan singkat tentang tanaman ini.",
                "rows": 4,
            }),
        }

    def clean_nama_panggilan(self):
        nama = strip_tags(self.cleaned_data.get("nama_panggilan", "")).strip()
        if not nama:
            raise ValidationError("Nama panggilan tanaman tidak boleh kosong atau hanya berisi tag HTML.")
        return nama

    def clean_lokasi(self):
        lokasi = strip_tags(self.cleaned_data.get("lokasi", "")).strip()
        return lokasi

    def clean_catatan(self):
        catatan = strip_tags(self.cleaned_data.get("catatan", "")).strip()
        return catatan


class JurnalPertumbuhanForm(forms.ModelForm):
    """Form untuk mencatat log perkembangan berkala tanaman."""

    class Meta:
        model = JurnalPertumbuhan
        fields = ["tanggal", "catatan", "foto"]
        widgets = {
            "tanggal": forms.DateInput(attrs={"id": "tanggal", "type": "date", "required": True}),
            "catatan": forms.Textarea(attrs={
                "id": "catatan",
                "placeholder": "Misalnya: muncul dua daun baru, media tanam diganti.",
                "rows": 3,
            }),
        }

    def clean_catatan(self):
        catatan = strip_tags(self.cleaned_data.get("catatan", "")).strip()
        return catatan
