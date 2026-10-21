from django.test import TestCase
from django.test import Client, override_settings
from io import BytesIO
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch
from time import time

from joserfc import jwt
from joserfc.jwk import RSAKey

import requests
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from .models import DeletedGoogleAccount, Profile

# Create your tests here.


User = get_user_model()
GOOGLE_SETTINGS = {
    'GOOGLE_CLIENT_ID': 'test-client.apps.googleusercontent.com',
    'GOOGLE_CLIENT_SECRET': 'test-secret',

}


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

    def test_remove_photo_clears_google_and_upload(self):
        self.login()
        self.user.profile.google_photo_url = 'https://example.com/avatar.jpg'
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

    @override_settings(GOOGLE_CLIENT_ID='', GOOGLE_CLIENT_SECRET='')
    def test_login_without_credentials_is_available_but_disabled(self):
        response = self.client.get(reverse('akun:login'))
        self.assertContains(response, 'disabled')
        self.assertContains(response, 'Login Google belum tersedia')


@override_settings(**GOOGLE_SETTINGS)
class GoogleLoginTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.signing_key = RSAKey.generate_key(2048, parameters={'kid': 'test-google'})

    def setUp(self):
        self.claims = {
            'sub': 'google-id-1', 'email': 'fatih@example.com', 'email_verified': True,
            'name': 'Nama OAuth', 'given_name': 'Fatih', 'picture': 'https://example.com/oauth.jpg',
        }
        self.token_key = self.signing_key
        metadata = {
            'issuer': 'https://accounts.google.com',
            'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_endpoint': 'https://oauth2.googleapis.com/token',
            'jwks_uri': 'https://www.googleapis.com/oauth2/v3/certs',
            'id_token_signing_alg_values_supported': ['RS256'],
        }
        app = 'authlib.integrations.django_client.apps.DjangoOAuth2App'
        patches = [
            patch(app + '.load_server_metadata', return_value=metadata),
            patch(app + '.fetch_jwk_set', return_value={'keys': [self.signing_key.as_dict()]}),
            patch(app + '.fetch_access_token', side_effect=self.google_token),
            patch('akun.views.requests.get', return_value=Mock(**{
                'json.return_value': {'names': [{'displayName': 'Fatih dari Google'}], 'photos': [{'url': 'https://example.com/people.jpg'}]},
            })),
        ]
        mocks = []
        for item in patches:
            mocks.append(item.start())
            self.addCleanup(item.stop)
        self.mock_token, self.mock_people = mocks[2:]

    def google_token(self, **kwargs):
        claims = {
            'iss': 'https://accounts.google.com', 'aud': GOOGLE_SETTINGS['GOOGLE_CLIENT_ID'],
            'iat': int(time()), 'exp': int(time()) + 300, 'nonce': self.nonce, **self.claims,
        }
        return {
            'access_token': 'test-token', 'token_type': 'Bearer',
            'id_token': jwt.encode({'alg': 'RS256', 'kid': 'test-google'}, claims, self.token_key),
        }

    def begin_login(self, next_url=''):
        response = self.client.post(reverse('akun:google_login'), {'next': next_url})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).hostname, 'accounts.google.com')
        params = parse_qs(urlparse(response.url).query)
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertIn('openid', params['scope'][0])
        self.assertEqual(params['redirect_uri'], ['http://testserver/login/google/callback/'])
        self.nonce = params['nonce'][0]
        return params['state'][0]

    def complete_login(self, state=None):
        state = state or self.begin_login()
        return self.client.get(reverse('akun:google_callback'), {'code': 'test-code', 'state': state})

    def test_first_login_creates_user_profile_from_people_api(self):
        response = self.complete_login()
        self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)
        user = User.objects.get(email='fatih@example.com')
        self.assertEqual(user.profile.display_name, 'Fatih dari Google')
        self.assertEqual(user.profile.google_photo_url, 'https://example.com/people.jpg')
        self.assertEqual(user.profile.google_id, 'google-id-1')
        self.assertFalse(user.has_usable_password())
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertNotIn('test-token', str(dict(self.client.session)))
        self.assertNotIn('id_token', self.client.session)
        self.assertIn('code_verifier', self.mock_token.call_args.kwargs)
        self.mock_people.assert_called_once_with(
            'https://people.googleapis.com/v1/people/me', params={'personFields': 'names,photos'},
            headers={'Authorization': 'Bearer test-token'}, timeout=5,
        )

    def test_repeat_login_does_not_duplicate_or_overwrite_profile(self):
        self.complete_login()
        user = User.objects.get()
        user.profile.display_name = 'Nama pilihanku'
        user.profile.bio = 'Bio pilihanku'
        user.profile.save()
        self.client.logout()
        self.complete_login()
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.display_name, 'Nama pilihanku')
        self.assertEqual(user.profile.bio, 'Bio pilihanku')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.mock_people.call_count, 1)

    def test_people_api_failure_uses_oauth_profile(self):
        self.mock_people.side_effect = requests.Timeout()
        self.complete_login()
        profile = Profile.objects.get()
        self.assertEqual(profile.display_name, 'Nama OAuth')
        self.assertEqual(profile.google_photo_url, 'https://example.com/oauth.jpg')

    def test_unexpected_people_api_data_uses_oauth_profile(self):
        self.mock_people.return_value.json.return_value = {'names': [None], 'photos': 'unexpected'}
        self.complete_login()
        self.assertEqual(Profile.objects.get().display_name, 'Nama OAuth')

    def test_non_https_google_photo_is_not_displayed(self):
        self.mock_people.return_value.json.return_value = {'photos': [{'url': 'javascript:alert(1)'}]}
        self.complete_login()
        self.assertEqual(Profile.objects.get().google_photo_url, '')

    def test_invalid_state_does_not_exchange_code_or_create_user(self):
        self.begin_login()
        response = self.complete_login('invalid-state')
        self.assertContains(response, 'Belum berhasil masuk', status_code=401)
        self.assertFalse(User.objects.exists())
        self.mock_token.assert_not_called()

    def test_state_cannot_be_replayed(self):
        state = self.begin_login()
        self.complete_login(state)
        self.client.logout()
        self.mock_token.reset_mock()
        response = self.complete_login(state)
        self.assertContains(response, 'Belum berhasil masuk', status_code=401)
        self.mock_token.assert_not_called()
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_nonce_is_rejected(self):
        self.claims['nonce'] = 'wrong-nonce'
        response = self.complete_login()
        self.assertContains(response, 'Belum berhasil masuk', status_code=401)
        self.assertFalse(User.objects.exists())

    def test_wrong_signature_is_rejected(self):
        self.token_key = RSAKey.generate_key(2048, parameters={'kid': 'test-google'})
        response = self.complete_login()
        self.assertContains(response, 'Belum berhasil masuk', status_code=401)
        self.assertFalse(User.objects.exists())

    def test_wrong_issuer_audience_and_expiry_are_rejected(self):
        for claim, value in [('iss', 'https://untrusted.example'), ('aud', 'another-client'), ('exp', int(time()) - 3600)]:
            with self.subTest(claim=claim):
                self.claims[claim] = value
                response = self.complete_login()
                self.assertContains(response, 'Belum berhasil masuk', status_code=401)
                self.assertFalse(User.objects.exists())
                del self.claims[claim]

    def test_unverified_email_is_rejected(self):
        self.claims['email_verified'] = False
        response = self.complete_login()
        self.assertContains(response, 'Belum berhasil masuk', status_code=401)
        self.assertFalse(User.objects.exists())

    def test_email_match_does_not_link_to_existing_django_account(self):
        existing = User.objects.create_user('admin-user', email='fatih@example.com')
        self.complete_login()
        user = User.objects.get(profile__google_id='google-id-1')
        self.assertNotEqual(user.pk, existing.pk)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_google_cancellation_has_friendly_message(self):
        state = self.begin_login()
        response = self.client.get(reverse('akun:google_callback'), {'error': 'access_denied', 'state': state})
        self.assertContains(response, 'Proses masuk dibatalkan', status_code=401)
        self.assertFalse(User.objects.exists())

    def test_deleted_google_account_cannot_login_or_register_again(self):
        self.complete_login()
        user = User.objects.get()
        self.client.post(reverse('akun:remove_account'), {'confirmation': user.profile.display_name})
        self.assertFalse(User.objects.exists())
        self.assertFalse(Profile.objects.exists())
        record = DeletedGoogleAccount.objects.get()
        self.assertEqual(record.fingerprint, DeletedGoogleAccount.fingerprint_for('google-id-1'))
        for _ in range(2):
            response = self.complete_login()
            self.assertContains(response, 'Akun ini telah dihapus permanen', status_code=403)
            self.assertNotIn('_auth_user_id', self.client.session)
            self.assertFalse(User.objects.exists())
            self.assertFalse(Profile.objects.exists())

    def test_another_google_identity_can_still_register(self):
        self.complete_login()
        user = User.objects.get()
        self.client.post(reverse('akun:remove_account'), {'confirmation': user.profile.display_name})
        self.claims.update(sub='different-google-id', email='another@example.com')
        response = self.complete_login()
        self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Profile.objects.get().google_id, 'different-google-id')

    def test_admin_deletion_also_blocks_deleted_google_identity(self):
        self.complete_login()
        User.objects.get().delete()
        self.client.logout()
        response = self.complete_login()
        self.assertContains(response, 'Akun ini telah dihapus permanen', status_code=403)
        self.assertFalse(User.objects.exists())

    def test_external_next_cannot_redirect_outside_site(self):
        state = self.begin_login('https://untrusted.example/steal')
        response = self.complete_login(state)
        self.assertRedirects(response, reverse('akun:my_profile'), fetch_redirect_response=False)

    def test_local_next_is_preserved(self):
        next_url = reverse('akun:edit_profile')
        state = self.begin_login(next_url)
        self.assertRedirects(self.complete_login(state), next_url, fetch_redirect_response=False)

    def test_oauth_start_requires_post_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('akun:google_login')).status_code, 403)
        self.assertEqual(client.get(reverse('akun:google_login')).status_code, 405)
        self.assertEqual(client.get(reverse('akun:google_callback')).status_code, 401)

    def test_auth_routes_have_no_account_prefix(self):
        self.assertEqual(reverse('akun:login'), '/login/')
        self.assertEqual(reverse('akun:logout'), '/logout/')
        self.assertEqual(reverse('akun:my_profile'), '/profil/')
        self.assertEqual(self.client.get('/akun/login/').status_code, 404)
