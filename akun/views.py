from uuid import uuid4

import requests
from authlib.common.errors import AuthlibBaseError
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from joserfc.errors import JoseError

from akun.forms import AccountRemovalForm, ProfileForm
from akun.models import DeletedGoogleAccount, Profile

def own_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user, defaults={
        'display_name': (user.get_full_name() or user.get_username())[:100],
    })
    return profile


def google_client():
    return OAuth().register(
        'google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile', 'code_challenge_method': 'S256', 'default_timeout': 5},
    )


def google_profile(token, info):
    name, photo = info.get('name', ''), info.get('picture', '')
    try:
        response = requests.get(
            'https://people.googleapis.com/v1/people/me',
            params={'personFields': 'names,photos'},
            headers={'Authorization': f"Bearer {token['access_token']}"},
            timeout=5,
        )
        response.raise_for_status()
        person = response.json()
        if isinstance(person, dict):
            for key, field in [('names', 'displayName'), ('photos', 'url')]:
                values = person.get(key)
                if isinstance(values, list) and values and isinstance(values[0], dict):
                    value = values[0].get(field)
                    if isinstance(value, str) and value.strip():
                        if key == 'names':
                            name = value
                        else:
                            photo = value
    except (requests.RequestException, ValueError, KeyError):
        pass  # Fall back to the verified Google profile if People API is unavailable.
    try:
        if not isinstance(photo, str) or len(photo) > 1000:
            raise ValidationError('Invalid photo URL')
        URLValidator(schemes=['https'])(photo)
    except ValidationError:
        photo = ''
    return str(name)[:100], photo


@require_GET
def login_view(request):
    if request.user.is_authenticated:
        return redirect('akun:my_profile')
    context = {
        'google_configured': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        'next': request.GET.get('next', ''),
    }
    return render(request, 'akun/login.html', context)


@require_POST
def google_login(request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        messages.error(request, 'Login Google belum tersedia.')
        return redirect('akun:login')
    next_url = request.POST.get('next', '')
    request.session['google_next'] = next_url if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ) else ''
    try:
        return google_client().authorize_redirect(request, request.build_absolute_uri(reverse('akun:google_callback')))
    except (AuthlibBaseError, requests.RequestException, ValueError):
        messages.error(request, 'Belum berhasil masuk. Silakan coba lagi.')
        return redirect('akun:login')


@require_GET
def google_callback(request):
    context = {'google_configured': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)}
    try:
        token = google_client().authorize_access_token(request)
        info = token.get('userinfo') or {}
        uid = info.get('sub', '')
        if not token.get('id_token') or not uid or len(uid) > 255 or info.get('email_verified') is not True:
            raise ValueError('Missing verified Google identity')
        with transaction.atomic():
            profile = Profile.objects.select_for_update().select_related('user').filter(google_id=uid).first()
            if DeletedGoogleAccount.objects.filter(fingerprint=DeletedGoogleAccount.fingerprint_for(uid)).exists():
                messages.error(request, 'Akun ini telah dihapus permanen dan tidak dapat digunakan kembali.')
                return render(request, 'akun/login.html', context, status=403)
            if profile is None:
                name, photo = google_profile(token, info)
                user = get_user_model().objects.create_user(
                    username=f'google_{uuid4().hex}', email=info.get('email', ''),
                    first_name=info.get('given_name', '')[:150], last_name=info.get('family_name', '')[:150],
                )
                profile = own_profile(user)
                profile.google_id = uid
                profile.display_name = name or user.get_full_name()[:100] or user.get_username()
                profile.google_photo_url = photo
                profile.save()
            if not profile.user.is_active:
                raise ValueError('Account is unavailable')
        login(request, profile.user)
        next_url = request.session.pop('google_next', '')
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(next_url)
        return redirect('akun:my_profile')
    except (AuthlibBaseError, JoseError, requests.RequestException, ValueError):
        request.session.pop('google_next', None)
        notice = 'Proses masuk dibatalkan.' if request.GET.get('error') == 'access_denied' else 'Belum berhasil masuk. Silakan coba lagi.'
        messages.error(request, notice)
        return render(request, 'akun/login.html', context, status=401)


@login_required
@require_GET
def my_profile(request):
    return redirect(own_profile(request.user))


@require_GET
def public_profile(request, user_id):
    profile = get_object_or_404(Profile.objects.select_related('user'), user_id=user_id, user__is_active=True)
    context = {'profile': profile, 'is_owner': request.user.pk == profile.user_id}
    return render(request, 'akun/profile.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def edit_profile(request):
    profile = own_profile(request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('akun:my_profile')
    return render(request, 'akun/edit_profile.html', {'profile': profile, 'form': form})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Kamu sudah keluar dari Floranity.')
    return redirect('akun:login')


@login_required
@require_http_methods(['GET', 'POST'])
def remove_account(request):
    profile = own_profile(request.user)
    form = AccountRemovalForm(request.POST or None, profile=profile)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            request.user.delete()
        logout(request)
        messages.success(request, 'Akun dan profilmu telah dihapus permanen dan tidak dapat dipulihkan.')
        return redirect('akun:login')
    return render(request, 'akun/remove_account.html', {'profile': profile, 'form': form})
