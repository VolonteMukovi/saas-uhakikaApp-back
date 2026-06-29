"""Tests unitaires de la vérification du jeton Google."""
import base64
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from inscription.services.google_oauth import ErreurConnexionGoogle, verifier_id_token_google


def _fake_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return f'{header}.{body}.signature'


@override_settings(GOOGLE_OAUTH_CLIENT_IDS=['server-client.apps.googleusercontent.com'])
class VerifierIdTokenGoogleTests(SimpleTestCase):
    def test_format_invalide(self):
        with self.assertRaises(ErreurConnexionGoogle) as ctx:
            verifier_id_token_google('pas-un-jwt')
        self.assertEqual(ctx.exception.code, 'invalid_token_format')

    @patch('inscription.services.google_oauth.id_token.verify_oauth2_token')
    def test_audience_mismatch_apres_verification(self, mock_verify):
        mock_verify.return_value = {
            'sub': '123',
            'email': 'a@b.com',
            'email_verified': True,
            'iss': 'https://accounts.google.com',
            'aud': 'autre-client.apps.googleusercontent.com',
        }
        with self.assertRaises(ErreurConnexionGoogle) as ctx:
            verifier_id_token_google(_fake_jwt({'aud': 'autre-client.apps.googleusercontent.com'}))
        self.assertEqual(ctx.exception.code, 'audience_mismatch')
        self.assertIsNotNone(ctx.exception.hint)

    @patch('inscription.services.google_oauth.id_token.verify_oauth2_token')
    def test_jeton_valide(self, mock_verify):
        mock_verify.return_value = {
            'sub': '123',
            'email': 'a@b.com',
            'email_verified': True,
            'iss': 'https://accounts.google.com',
            'aud': 'server-client.apps.googleusercontent.com',
        }
        payload = verifier_id_token_google(_fake_jwt({'aud': 'server-client.apps.googleusercontent.com'}))
        self.assertEqual(payload['sub'], '123')

    @patch('inscription.services.google_oauth.id_token.verify_oauth2_token')
    def test_audience_mismatch_avant_verification(self, mock_verify):
        mock_verify.side_effect = ValueError('Token has wrong audience')
        token = _fake_jwt({'aud': 'frontend-only.apps.googleusercontent.com'})
        with self.assertRaises(ErreurConnexionGoogle) as ctx:
            verifier_id_token_google(token)
        self.assertEqual(ctx.exception.code, 'audience_mismatch')

    @patch('inscription.services.google_oauth._verifier_via_tokeninfo_google')
    @patch('inscription.services.google_oauth.id_token.verify_oauth2_token')
    def test_fallback_tokeninfo_si_horloge_locale(self, mock_verify, mock_tokeninfo):
        mock_verify.side_effect = ValueError('Token expired, 100 < 200')
        mock_tokeninfo.return_value = {
            'sub': '123',
            'email': 'a@b.com',
            'email_verified': True,
            'iss': 'https://accounts.google.com',
            'aud': 'server-client.apps.googleusercontent.com',
        }
        payload = verifier_id_token_google(_fake_jwt({'aud': 'server-client.apps.googleusercontent.com', 'exp': 1}))
        self.assertEqual(payload['sub'], '123')
        mock_tokeninfo.assert_called_once()
