from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import DeletedAccount, Profile


User = get_user_model()


def uploaded_photo(name='plant.png'):
    output = BytesIO()
    Image.new('RGB', (40, 60), '#1b4d3e').save(output, format='PNG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')


class ProfileTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.media_settings = override_settings(MEDIA_ROOT=self.media.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)
        self.user = User.objects.create_user('fatih', email='private@example.com', first_name='Fatih')
        self.other = User.objects.create_user('rama', email='rama@example.com')

    def login(self):
        self.client.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')

    def test_profile_created_once_with_user(self):
        self.assertEqual(self.user.profile.display_name, 'Fatih')
        self.user.save()
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

    def test_public_profile_hides_private_email_and_owner_controls(self):
        response = self.client.get(self.user.profile.get_absolute_url())
        self.assertContains(response, 'Fatih')
        self.assertNotContains(response, self.user.email)
        self.assertNotContains(response, 'Edit profil')
        self.assertNotContains(response, 'Hapus akun permanen')

    def test_owner_can_see_email_and_controls(self):
        self.login()
        response = self.client.get(self.user.profile.get_absolute_url())
        self.assertContains(response, self.user.email)
        self.assertContains(response, 'Edit profil')
        self.assertContains(response, 'Hapus akun permanen')

    def test_inactive_or_missing_profiles_return_404(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get(self.user.profile.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse('akun:public_profile', args=[9999])).status_code, 404)

    def test_private_routes_require_login(self):
        for name in ['my_profile', 'edit_profile', 'remove_account']:
            with self.subTest(name=name):
                response = self.client.get(reverse(f'akun:{name}'))
                self.assertRedirects(response, f"{reverse('akun:login')}?next={reverse(f'akun:{name}')}", fetch_redirect_response=False)

    def test_profile_edit_only_updates_current_user(self):
        self.login()
        response = self.client.post(reverse('akun:edit_profile'), {
            'display_name': 'Kebun Fatih', 'bio': 'Merawat monstera.',
            'user': self.other.pk, 'user_id': self.other.pk,
        })
        self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)
        self.user.profile.refresh_from_db()
        self.other.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'Merawat monstera.')
        self.assertEqual(self.other.profile.display_name, 'rama')
        response = self.client.get(reverse('akun:edit_profile'))
        self.assertNotIn('theme', response.context['form'].fields)
        self.assertNotContains(response, 'Tema tampilan')
        self.assertNotContains(response, 'data-theme=')

    def test_invalid_profile_edit_does_not_change_database(self):
        self.login()
        for values in [
            {'display_name': '', 'bio': ''},
            {'display_name': 'A' * 101, 'bio': ''},
            {'display_name': 'Fatih', 'bio': 'A' * 501},
        ]:
            response = self.client.post(reverse('akun:edit_profile'), values)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, 'Fatih')

    def test_bio_html_is_escaped(self):
        self.user.profile.bio = '<script>alert(1)</script>'
        self.user.profile.save()
        response = self.client.get(self.user.profile.get_absolute_url())
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_photo_is_reencoded_and_replacement_removes_old_file(self):
        self.login()
        values = {'display_name': 'Fatih', 'bio': ''}
        self.client.post(reverse('akun:edit_profile'), {**values, 'photo': uploaded_photo()})
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.photo.name.endswith('.jpg'))
        with profile.photo.open('rb') as saved:
            image = Image.open(saved)
            self.assertEqual(image.format, 'JPEG')
            self.assertEqual(image.size, (512, 512))
        old_name, storage = profile.photo.name, profile.photo.storage
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('akun:edit_profile'), {**values, 'photo': uploaded_photo()})
        self.assertFalse(storage.exists(old_name))

    def test_fake_image_and_oversized_file_rejected(self):
        self.login()
        values = {'display_name': 'Fatih', 'bio': ''}
        for upload in [
            SimpleUploadedFile('fake.png', b'<script>bad</script>', content_type='image/png'),
            SimpleUploadedFile('big.png', uploaded_photo().read() + b'0' * (5 * 1024 * 1024), content_type='image/png'),
        ]:
            response = self.client.post(reverse('akun:edit_profile'), {**values, 'photo': upload})
            self.assertTrue(response.context['form'].errors.get('photo'))
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.photo)

    def test_remove_photo_clears_saved_url_and_upload(self):
        self.login()
        self.user.profile.photo_url = 'https://example.com/avatar.jpg'
        self.user.profile.photo = uploaded_photo()
        self.user.profile.save()
        name, storage = self.user.profile.photo.name, self.user.profile.photo.storage
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('akun:edit_profile'), {
                'display_name': 'Fatih', 'bio': '', 'remove_photo': 'on',
            })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.avatar_url, '')
        self.assertFalse(storage.exists(name))

    def test_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')
        for name in ['edit_profile', 'remove_account', 'logout']:
            self.assertEqual(client.post(reverse(f'akun:{name}'), {}).status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.user.pk, is_active=True).exists())

    def test_logout_only_accepts_post(self):
        self.login()
        self.assertEqual(self.client.get(reverse('akun:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.client.post(reverse('akun:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_account_removal_get_or_wrong_confirmation_changes_nothing(self):
        self.login()
        url = reverse('akun:remove_account')
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {'confirmation': 'wrong name'})
        self.assertTrue(response.context['form'].errors)
        self.assertTrue(User.objects.filter(pk=self.user.pk, is_active=True).exists())

    def test_delete_only_current_user_and_remove_public_profile(self):
        self.login()
        url = self.user.profile.get_absolute_url()
        self.client.post(reverse('akun:remove_account'), {
            'confirmation': 'Fatih', 'user_id': self.other.pk,
        })
        self.other.refresh_from_db()
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(self.other.is_active)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

    def test_removal_page_only_offers_permanent_deletion(self):
        self.login()
        response = self.client.get(reverse('akun:remove_account'))
        self.assertContains(response, 'Hapus akun permanen')
        self.assertNotContains(response, 'Nonaktifkan')
        self.assertEqual(list(response.context['form'].fields), ['confirmation'])

    def test_delete_account_cascades_profile_and_photo(self):
        self.login()
        self.user.profile.photo = uploaded_photo()
        self.user.profile.save()
        name, storage = self.user.profile.photo.name, self.user.profile.photo.storage
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('akun:remove_account'), {'confirmation': 'Fatih'})
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Profile.objects.filter(user_id=self.user.pk).exists())
        self.assertFalse(storage.exists(name))
        self.assertTrue(User.objects.filter(pk=self.other.pk).exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_old_account_profile_is_created_when_opening_my_profile(self):
        self.user.profile.delete()
        self.login()
        self.client.get(reverse('akun:my_profile'))
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)


class AuthenticationTests(TestCase):
    password = 'Tanaman!Hujan#4729'

    def register(self, username='pecintadaun', **extra):
        return self.client.post(reverse('akun:register'), {
            'username': username,
            'password1': self.password,
            'password2': self.password,
            **extra,
        })

    def create_user(self, **extra):
        return User.objects.create_user('pecintadaun', password=self.password, **extra)

    def test_auth_pages_offer_username_password_without_google(self):
        for name in ('login', 'register'):
            response = self.client.get(reverse(f'akun:{name}'))
            self.assertContains(response, 'name="username"')
            self.assertContains(response, 'type="password"')
            self.assertNotContains(response, 'Lanjutkan dengan Google')
            self.assertNotContains(response, 'disabled')
        self.assertContains(self.client.get(reverse('akun:login')), reverse('akun:register'))
        self.assertContains(self.client.get(reverse('akun:register')), reverse('akun:login'))

    def test_registration_hashes_password_and_creates_profile(self):
        response = self.register(is_staff='on', is_superuser='on')
        self.assertRedirects(response, reverse('akun:login'))
        user = User.objects.get(username='pecintadaun')
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.profile.display_name, 'pecintadaun')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_validates_passwords_and_username(self):
        for values in (
            {'password2': 'Different!Password#4729'},
            {'password1': '123', 'password2': '123'},
            {'username': ''},
            {'username': '<script>bad</script>'},
        ):
            with self.subTest(values=values):
                response = self.register(**values)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.assertFalse(User.objects.exists())
                self.assertFalse(Profile.objects.exists())

    def test_duplicate_username_cannot_overwrite_account(self):
        user = self.create_user()
        response = self.register(username='PECINTADAUN')
        self.assertTrue(response.context['form'].errors.get('username'))
        self.assertEqual(User.objects.count(), 1)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.password))

    def test_empty_posts_show_required_errors(self):
        for name in ('login', 'register'):
            response = self.client.post(reverse(f'akun:{name}'), {})
            self.assertTrue(response.context['form'].is_bound)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_login_creates_session_and_opens_own_profile(self):
        user = self.create_user()
        response = self.client.post(reverse('akun:login'), {
            'username': user.username, 'password': self.password,
        })
        self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
        self.assertRedirects(self.client.get(reverse('akun:my_profile')), user.profile.get_absolute_url())

    def test_wrong_password_or_missing_user_cannot_login(self):
        self.create_user()
        for username, password in [('pecintadaun', 'wrong'), ('unknown', self.password)]:
            response = self.client.post(reverse('akun:login'), {
                'username': username, 'password': password,
            })
            self.assertTrue(response.context['form'].non_field_errors())
            self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_user_cannot_login(self):
        user = self.create_user(is_active=False)
        response = self.client.post(reverse('akun:login'), {
            'username': user.username, 'password': self.password,
        })
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_existing_account_needs_usable_password(self):
        user = User.objects.create_user('akunlama')
        response = self.client.post(reverse('akun:login'), {
            'username': user.username, 'password': self.password,
        })
        self.assertTrue(response.context['form'].errors)
        user.set_password(self.password)
        user.save()
        response = self.client.post(reverse('akun:login'), {
            'username': user.username, 'password': self.password,
        })
        self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 1)

    def test_login_preserves_local_next_even_after_invalid_password(self):
        user = self.create_user()
        next_url = reverse('akun:edit_profile')
        response = self.client.post(reverse('akun:login'), {
            'username': user.username, 'password': 'wrong', 'next': next_url,
        })
        self.assertContains(response, f'value="{next_url}"')
        response = self.client.post(reverse('akun:login'), {
            'username': user.username, 'password': self.password, 'next': next_url,
        })
        self.assertRedirects(response, next_url)

    def test_login_rejects_external_redirects(self):
        user = self.create_user()
        for next_url in ('https://example.com/', '//example.com/', 'javascript:alert(1)', r'/\example.com/'):
            with self.subTest(next=next_url):
                self.client.logout()
                response = self.client.post(reverse('akun:login'), {
                    'username': user.username, 'password': self.password, 'next': next_url,
                })
                self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)

    def test_authenticated_users_skip_login_and_registration(self):
        self.client.force_login(self.create_user())
        for name in ('login', 'register'):
            self.assertRedirects(
                self.client.get(reverse(f'akun:{name}')),
                reverse('akun:my_profile'), fetch_redirect_response=False,
            )
        self.assertEqual(User.objects.count(), 1)

    def test_registration_and_login_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for name in ('login', 'register'):
            self.assertEqual(client.post(reverse(f'akun:{name}'), {}).status_code, 403)

    def test_register_login_logout_with_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('akun:register'))
        response = client.post(reverse('akun:register'), {
            'username': 'kebunbaru', 'password1': self.password, 'password2': self.password,
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertRedirects(response, reverse('akun:login'))
        response = client.post(reverse('akun:login'), {
            'username': 'kebunbaru', 'password': self.password,
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)
        response = client.get(reverse('akun:edit_profile'))
        self.assertContains(response, 'Informasi profil')
        response = client.post(reverse('akun:logout'), {
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertRedirects(response, reverse('akun:login'))
        self.assertNotIn('_auth_user_id', client.session)

    def test_deleted_account_cannot_login_or_register_again(self):
        user = self.create_user()
        self.client.force_login(user)
        self.client.post(reverse('akun:remove_account'), {'confirmation': user.profile.display_name})
        self.assertFalse(User.objects.exists())
        self.assertFalse(Profile.objects.exists())
        self.assertEqual(
            DeletedAccount.objects.get().fingerprint,
            DeletedAccount.fingerprint_for(user.username),
        )
        response = self.client.post(reverse('akun:login'), {
            'username': user.username, 'password': self.password,
        })
        self.assertTrue(response.context['form'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)
        for username in ('pecintadaun', 'PECINTADAUN', 'ｐｅｃｉｎｔａｄａｕｎ'):
            response = self.register(username=username)
            self.assertTrue(response.context['form'].errors.get('username'))
            self.assertFalse(User.objects.exists())
        self.assertRedirects(self.register(username='kebunlain'), reverse('akun:login'))

    def test_admin_deletion_also_prevents_username_reuse(self):
        user = self.create_user()
        user.delete()
        response = self.register()
        self.assertTrue(response.context['form'].errors.get('username'))
        self.assertFalse(User.objects.exists())

    def test_auth_routes_have_no_account_prefix_or_google_flow(self):
        self.assertEqual(reverse('akun:login'), '/login/')
        self.assertEqual(reverse('akun:register'), '/register/')
        self.assertEqual(reverse('akun:logout'), '/logout/')
        for path in ('/akun/login/', '/login/google/', '/login/google/callback/'):
            self.assertEqual(self.client.get(path).status_code, 404)
