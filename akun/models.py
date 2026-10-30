from hashlib import sha256
from pathlib import Path
from unicodedata import normalize
from uuid import uuid4

from django.conf import settings
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse

# Create your models here.


def profile_photo_path(instance, filename):
    return f'profiles/{instance.user_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class Profile(models.Model):
    id = models.BigAutoField(primary_key=True)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField('Nama tampilan', max_length=100)
    bio = models.TextField('Bio', max_length=500, blank=True)
    photo = models.ImageField('Foto profil', upload_to=profile_photo_path, blank=True)
    photo_url = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    @property
    def avatar_url(self):
        return self.photo.url if self.photo else self.photo_url

    @property
    def initials(self):
        return ''.join(part[0] for part in self.display_name.split()[:2]).upper() or 'F'

    def get_absolute_url(self):
        return reverse('akun:public_profile', args=[self.user_id])


class DeletedAccount(models.Model):
    # Keep only a stable fingerprint, without retaining the deleted profile.
    fingerprint = models.CharField(max_length=64, primary_key=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def fingerprint_for(username):
        username = normalize('NFKC', username).casefold()
        return sha256(f'username:{username}'.encode()).hexdigest()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        Profile.objects.get_or_create(user=instance, defaults={
            'display_name': (instance.get_full_name() or instance.get_username())[:100],
        })


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def block_deleted_account(sender, instance, using, **kwargs):
    DeletedAccount.objects.using(using).get_or_create(
        fingerprint=DeletedAccount.fingerprint_for(instance.get_username()),
    )


def delete_after_commit(photo):
    if photo:
        storage, name = photo.storage, photo.name
        transaction.on_commit(lambda: storage.delete(name))


@receiver(pre_save, sender=Profile)
def remove_replaced_photo(sender, instance, **kwargs):
    if instance.pk:
        previous = Profile.objects.filter(pk=instance.pk).first()
        if previous and previous.photo and previous.photo != instance.photo:
            delete_after_commit(previous.photo)


@receiver(post_delete, sender=Profile)
def remove_deleted_photo(sender, instance, **kwargs):
    delete_after_commit(instance.photo)
