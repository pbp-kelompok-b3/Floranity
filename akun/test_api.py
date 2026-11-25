from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from koleksi.models import Tanaman
from .models import DeletedAccount, Profile


def uploaded_photo():
    output = BytesIO()
    Image.new('RGB', (60, 90), '#14532d').save(output, format='PNG')
    return SimpleUploadedFile('plant.png', output.getvalue(), content_type='image/png')


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AccountAPITests(APITestCase):
    password = 'Garden!47Quiet'

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = get_user_model().objects.create_user(
            username='pemilik', password=self.password, email='private@example.com',
        )
        self.other = get_user_model().objects.create_user('anggota_lain', password=self.password)
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def csrf(self):
        response = self.client.get(reverse('akun_api:csrf'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', self.client.cookies)
        return response.data['csrfToken']

    def mutate(self, method, name, data=None, format='json', **kwargs):
        return getattr(self.client, method)(
            reverse(f'akun_api:{name}', kwargs=kwargs), data or {}, format=format,
            HTTP_X_CSRFTOKEN=self.csrf(),
        )

    def login(self):
        response = self.mutate('post', 'login', {
            'username': self.user.username, 'password': self.password,
        })
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def test_public_auth_endpoints_require_csrf_even_when_anonymous(self):
        for endpoint, data in [
            ('register', {'username': 'newgardener', 'password1': self.password, 'password2': self.password}),
            ('login', {'username': self.user.username, 'password': self.password}),
        ]:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(f'akun_api:{endpoint}'), data, format='json')
                self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.filter(username='newgardener').exists())

    def test_register_hashes_password_and_creates_profile_without_logging_in(self):
        response = self.mutate('post', 'register', {
            'username': 'newgardener', 'password1': self.password, 'password2': self.password,
        })
        self.assertEqual(response.status_code, 201, response.data)
        user = get_user_model().objects.get(username='newgardener')
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
        self.assertEqual(response.data['user_id'], user.pk)
        self.assertNotIn('password', response.data)
        self.assertNotIn('password1', response.data)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_register_preserves_web_password_and_deleted_username_validation(self):
        get_user_model().objects.create_user('deleted_name').delete()
        for payload in [
            {'username': self.user.username, 'password1': self.password, 'password2': self.password},
            {'username': 'deleted_name', 'password1': self.password, 'password2': self.password},
            {'username': 'weak', 'password1': '123', 'password2': 'different'},
        ]:
            response = self.mutate('post', 'register', payload)
            self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='weak').exists())

    def test_login_and_web_share_the_same_django_session(self):
        response = self.login()
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.assertEqual(self.client.get(reverse('akun:edit_profile')).status_code, 200)
        self.assertEqual(self.client.get(reverse('akun_api:profile-me')).data['user_id'], self.user.pk)

    def test_web_login_can_access_private_api(self):
        response = self.client.post(reverse('akun:login'), {
            'username': self.user.username, 'password': self.password,
        }, HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse('akun_api:profile-me')).status_code, 200)

    def test_bad_credentials_and_inactive_users_cannot_log_in(self):
        for password, active in [('wrong', True), (self.password, False)]:
            self.user.is_active = active
            self.user.save()
            response = self.mutate('post', 'login', {'username': self.user.username, 'password': password})
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('_auth_user_id', self.client.session)

    def test_private_profile_requires_login_and_mutations_require_csrf(self):
        url = reverse('akun_api:profile-me')
        for method in ['get', 'patch', 'put', 'delete']:
            self.assertEqual(getattr(self.client, method)(url).status_code, 403)
        self.login()
        for method in ['patch', 'put', 'delete']:
            self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 403)
        self.assertEqual(self.client.post(reverse('akun_api:logout')).status_code, 403)

    def test_login_rotates_csrf_and_logout_clears_session(self):
        old_token = self.csrf()
        self.login()
        response = self.client.patch(reverse('akun_api:profile-me'), {'bio': 'blocked'},
                                     format='json', HTTP_X_CSRFTOKEN=old_token)
        self.assertEqual(response.status_code, 403)
        response = self.mutate('post', 'logout')
        self.assertEqual(response.status_code, 204)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('akun_api:profile-me')).status_code, 403)

    def test_public_profile_is_read_only_and_never_exposes_private_fields(self):
        url = reverse('akun_api:profile-detail', args=[self.user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('email', response.data)
        self.assertNotIn('username', response.data)
        self.assertNotIn('password', response.data)
        self.assertEqual(response.data['display_name'], self.user.profile.display_name)
        self.login()
        response = self.client.delete(url, {}, format='json', HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 405)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse('akun_api:profile-detail', args=[999999])).status_code, 404)

    def test_patch_only_changes_current_profile_and_preserves_missing_fields(self):
        self.login()
        response = self.mutate('patch', 'profile-me', {
            'bio': 'Cerita hijau baru.', 'user_id': self.other.pk,
            'username': 'hijacked', 'email': 'changed@example.com',
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.other.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'Cerita hijau baru.')
        self.assertEqual(self.user.profile.display_name, 'pemilik')
        self.assertEqual(self.user.username, 'pemilik')
        self.assertEqual(self.user.email, 'private@example.com')
        self.assertEqual(self.other.profile.bio, '')

    def test_put_and_invalid_profile_fields_follow_form_validation(self):
        self.login()
        for body in [{'display_name': ''}, {'display_name': 'x' * 101}, {'bio': 'x' * 501}]:
            self.assertEqual(self.mutate('patch', 'profile-me', body).status_code, 400)
        self.assertEqual(self.mutate('put', 'profile-me', {'bio': 'missing required name'}).status_code, 400)
        response = self.mutate('put', 'profile-me', {'display_name': 'Kebun saya', 'bio': 'Bio baru.'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['display_name'], 'Kebun saya')
        self.assertEqual(response.data['bio'], 'Bio baru.')

    def test_photo_upload_reencodes_replaces_and_removes_files(self):
        self.login()
        response = self.mutate('patch', 'profile-me', {'photo': uploaded_photo()}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['avatar_url'].startswith('http://testserver/media/'))
        self.user.profile.refresh_from_db()
        with Image.open(self.user.profile.photo.path) as image:
            self.assertEqual(image.size, (512, 512))
            self.assertEqual(image.format, 'JPEG')
        old_name = self.user.profile.photo.name
        storage = self.user.profile.photo.storage
        with self.captureOnCommitCallbacks(execute=True):
            response = self.mutate('patch', 'profile-me', {'photo': uploaded_photo()}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(storage.exists(old_name))
        self.user.profile.refresh_from_db()
        old_name = self.user.profile.photo.name
        self.user.profile.photo_url = 'https://example.com/old-avatar.png'
        self.user.profile.save()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.mutate('patch', 'profile-me', {'remove_photo': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['avatar_url'], '')
        self.assertFalse(storage.exists(old_name))

    def test_invalid_or_conflicting_photo_upload_is_rejected(self):
        self.login()
        fake = SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')
        response = self.mutate('patch', 'profile-me', {'photo': fake}, format='multipart')
        self.assertEqual(response.status_code, 400)
        response = self.mutate('patch', 'profile-me', {
            'photo': uploaded_photo(), 'remove_photo': 'true',
        }, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.photo)

    def test_deletion_requires_exact_confirmation_and_cascades_only_own_data(self):
        self.login()
        for data in [{}, {'confirmation': 'wrong'}]:
            self.assertEqual(self.mutate('delete', 'profile-me', data).status_code, 400)
            self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        plant = Tanaman.objects.create(pemilik=self.user, nama_panggilan='Monstera uji')
        self.user.profile.photo = uploaded_photo()
        self.user.profile.save()
        uid, name, storage = self.user.pk, self.user.profile.photo.name, self.user.profile.photo.storage
        with self.captureOnCommitCallbacks(execute=True):
            response = self.mutate('delete', 'profile-me', {
                'confirmation': self.user.profile.display_name, 'user_id': self.other.pk,
            })
        self.assertEqual(response.status_code, 204)
        self.assertFalse(get_user_model().objects.filter(pk=uid).exists())
        self.assertFalse(Profile.objects.filter(user_id=uid).exists())
        self.assertFalse(Tanaman.objects.filter(pk=plant.pk).exists())
        self.assertFalse(storage.exists(name))
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())
        self.assertTrue(DeletedAccount.objects.filter(
            fingerprint=DeletedAccount.fingerprint_for('pemilik'),
        ).exists())
        self.assertEqual(self.client.get(reverse('akun_api:profile-me')).status_code, 403)

    def test_head_and_browsable_api_are_available(self):
        self.login()
        response = self.client.head(reverse('akun_api:profile-me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        response = self.client.get(reverse('akun_api:profile-me'), HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rest_framework')
