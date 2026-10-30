from django.contrib.auth.models import User
from django.db import models


class Tanaman(models.Model):
    """Model untuk menyimpan tanaman dalam koleksi pribadi pengguna."""

    pemilik = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="koleksi_tanaman",
        null=True,
        blank=True,
        help_text="Pengguna pemilik koleksi tanaman ini",
    )
    spesies_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID referensi spesies dari Perenual (jika ada)",
    )
    nama_panggilan = models.CharField(
        max_length=150,
        help_text="Nama panggilan/pemberian pengguna untuk tanaman",
    )
    nama_ilmiah = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Nama ilmiah / spesies tanaman",
    )
    lokasi = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Lokasi tanaman diletakkan (misal: Balkon, Kamar)",
    )
    tanggal_mulai = models.DateField(
        null=True,
        blank=True,
        help_text="Tanggal mulai merawat tanaman",
    )
    cahaya = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Kebutuhan cahaya",
    )
    penyiraman = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Kebutuhan penyiraman",
    )
    tingkat_kesulitan = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Tingkat kesulitan perawatan",
    )
    foto = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL atau path foto tanaman",
    )
    catatan = models.TextField(
        blank=True,
        default="",
        help_text="Catatan tambahan mengenai tanaman",
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-dibuat_pada"]
        verbose_name = "Tanaman"
        verbose_name_plural = "Tanaman"

    def __str__(self):
        return self.nama_panggilan

    @property
    def jumlah_jurnal(self):
        """Menghitung total entri jurnal pertumbuhan untuk tanaman ini."""
        return self.jurnals.count()


class JurnalPertumbuhan(models.Model):
    """Model untuk mencatat perkembangan berkala (jurnal) suatu tanaman."""

    tanaman = models.ForeignKey(
        Tanaman,
        on_delete=models.CASCADE,
        related_name="jurnals",
        help_text="Tanaman yang dicatat",
    )
    tanggal = models.DateField(
        help_text="Tanggal pencatatan jurnal",
    )
    catatan = models.TextField(
        blank=True,
        default="",
        help_text="Catatan perkembangan atau perawatan tanaman",
    )
    foto = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL atau path foto perkembangan tanaman",
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-tanggal", "-dibuat_pada"]
        verbose_name = "Jurnal Pertumbuhan"
        verbose_name_plural = "Jurnal Pertumbuhan"

    def __str__(self):
        return f"Jurnal {self.tanaman.nama_panggilan} - {self.tanggal}"
