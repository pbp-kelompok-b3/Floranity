from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .models import Profile


class ProfileForm(forms.ModelForm):
    remove_photo = forms.BooleanField(required=False, label='Hapus foto profil (termasuk foto Google)')

    class Meta:
        model = Profile
        fields = ['display_name', 'bio', 'photo']
        widgets = {
            'display_name': forms.TextInput(attrs={'autocomplete': 'nickname', 'placeholder': 'Nama yang ingin kamu gunakan'}),
            'bio': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Ceritakan sedikit tentang kamu dan tanaman favoritmu…'}),
            'photo': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }
        help_texts = {
            'bio': 'Maksimal 500 karakter. Bio dapat dilihat oleh anggota lain.',
            'photo': 'JPG, PNG, atau WebP, maksimal 5 MB. Foto akan dipotong persegi.',
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo or not hasattr(photo, 'content_type'):
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Ukuran foto maksimal 5 MB.')
        if photo.image.format not in {'JPEG', 'PNG', 'WEBP'}:
            raise forms.ValidationError('Gunakan foto JPG, PNG, atau WebP.')
        if photo.image.width * photo.image.height > 25_000_000:
            raise forms.ValidationError('Resolusi foto terlalu besar. Maksimal 25 megapiksel.')
        # Re-encode to strip metadata and reject executable or mixed file content.
        photo.seek(0)
        with Image.open(photo) as source:
            image = ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'), (512, 512))
            output = BytesIO()
            image.save(output, format='JPEG', quality=88)
        return ContentFile(output.getvalue(), name='avatar.jpg')

    def clean(self):
        data = super().clean()
        if data.get('remove_photo') and self.files.get('photo'):
            self.add_error('photo', 'Pilih unggah foto baru atau hapus foto, bukan keduanya.')
        return data

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.cleaned_data.get('remove_photo'):
            profile.photo = ''
            profile.google_photo_url = ''
        if commit:
            profile.save()
        return profile


class AccountRemovalForm(forms.Form):
    confirmation = forms.CharField(label='Ketik nama tampilanmu untuk mengonfirmasi', max_length=100)

    def __init__(self, *args, profile, **kwargs):
        self.profile = profile
        super().__init__(*args, **kwargs)

    def clean_confirmation(self):
        value = self.cleaned_data['confirmation']
        if value != self.profile.display_name:
            raise forms.ValidationError('Nama tampilan tidak sesuai. Akun belum diubah.')
        return value
