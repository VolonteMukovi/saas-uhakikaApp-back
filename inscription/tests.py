"""Tests connexion Google OAuth."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from inscription.models import ProfilConnexionGoogle

User = get_user_model()

FAKE_GOOGLE_JWT = 'aaa.bbb.ccc'

PAYLOAD_GOOGLE = {
    'sub': 'google-sub-12345',
    'email': 'test@gmail.com',
    'email_verified': True,
    'given_name': 'Jean',
    'family_name': 'Dupont',
    'picture': 'https://lh3.googleusercontent.com/a/photo.jpg',
    'iss': 'https://accounts.google.com',
}


@override_settings(GOOGLE_OAUTH_CLIENT_IDS=['test-client-id.apps.googleusercontent.com'])
class ConnexionGoogleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('inscription.views.verifier_id_token_google')
    def test_inscription_google_nouveau_compte(self, mock_verify):
        mock_verify.return_value = PAYLOAD_GOOGLE
        resp = self.client.post('/api/inscription/google/', {
            'credential': FAKE_GOOGLE_JWT,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['est_nouveau_compte'])
        self.assertTrue(resp.data['connexion_google'])
        self.assertIn('tokens', resp.data)
        self.assertTrue(resp.data['a_entreprise'])
        self.assertEqual(resp.data['prochaine_etape'], 'utiliser_application')
        user = User.objects.get(email='test@gmail.com')
        self.assertFalse(user.has_usable_password())
        self.assertTrue(ProfilConnexionGoogle.objects.filter(utilisateur=user).exists())

    @patch('inscription.views.verifier_id_token_google')
    def test_connexion_google_compte_existant(self, mock_verify):
        mock_verify.return_value = PAYLOAD_GOOGLE
        user = User.objects.create_user(username='jean', email='test@gmail.com', password='x', role='admin')
        ProfilConnexionGoogle.objects.create(
            utilisateur=user,
            google_sub='google-sub-12345',
            email_google='test@gmail.com',
        )
        resp = self.client.post('/api/inscription/google/', {
            'id_token': FAKE_GOOGLE_JWT,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['est_nouveau_compte'])

    @patch('inscription.views.verifier_id_token_google')
    def test_liaison_email_existant_sans_google(self, mock_verify):
        mock_verify.return_value = PAYLOAD_GOOGLE
        User.objects.create_user(username='jean', email='test@gmail.com', password='motdepasse1', role='admin')
        resp = self.client.post('/api/inscription/google/', {
            'credential': FAKE_GOOGLE_JWT,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['est_nouveau_compte'])
        self.assertTrue(ProfilConnexionGoogle.objects.filter(google_sub='google-sub-12345').exists())

    def test_google_config_sans_client_id(self):
        with self.settings(GOOGLE_OAUTH_CLIENT_IDS=[]):
            resp = self.client.get('/api/inscription/google/config/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['actif'])

    @override_settings(GOOGLE_OAUTH_CLIENT_IDS=['abc.apps.googleusercontent.com'])
    def test_google_config_avec_client_id(self):
        resp = self.client.get('/api/inscription/google/config/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['actif'])
        self.assertIn('abc.apps.googleusercontent.com', resp.data['client_ids'])

    def test_google_sans_token(self):
        resp = self.client.post('/api/inscription/google/', {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_google_rejette_html_iframe(self):
        resp = self.client.post('/api/inscription/google/', {
            'credential': '<!DOCTYPE html><html><head><title>Sign In - Google Accounts</title></head></html>',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        detail = str(resp.data)
        self.assertIn('HTML', detail)

    def test_google_rejette_jeton_sans_format_jwt(self):
        resp = self.client.post('/api/inscription/google/', {
            'credential': 'CjEKK2ZrSU1LNVRzS1dKMG1nYmdRZEZ4SzVNZ2VTakpDanBtTkxHXzZZZW1NUVkaAmZyEgIIBQ==',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        detail = str(resp.data)
        self.assertIn('JWT', detail)

    @override_settings(GOOGLE_OAUTH_CLIENT_IDS=[])
    @patch('inscription.views.verifier_id_token_google')
    def test_google_non_configure(self, mock_verify):
        from inscription.services.google_oauth import ErreurConnexionGoogle
        mock_verify.side_effect = ErreurConnexionGoogle('Non configuré', code='google_not_configured')
        resp = self.client.post('/api/inscription/google/', {'credential': FAKE_GOOGLE_JWT}, format='json')
        self.assertEqual(resp.status_code, 503)
