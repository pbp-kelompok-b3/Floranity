from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from akun.forms import AccountRemovalForm, ProfileForm, RegisterForm
from akun.models import Profile


def own_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user, defaults={
        'display_name': (user.get_full_name() or user.get_username())[:100],
    })
    return profile


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('akun:my_profile')
    form = RegisterForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, 'Akun berhasil dibuat. Silakan masuk dengan username dan passwordmu.')
        return redirect('akun:login')
    return render(request, 'akun/login.html', {'form': form, 'is_register': True})


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('akun:my_profile')
    form = AuthenticationForm(request, data=request.POST if request.method == 'POST' else None)
    next_url = request.POST.get('next', request.GET.get('next', ''))
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        next_url = ''
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(next_url or 'akun:my_profile')
    return render(request, 'akun/login.html', {'form': form, 'next': next_url})


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
