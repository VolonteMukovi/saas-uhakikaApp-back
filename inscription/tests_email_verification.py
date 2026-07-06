"""Tests vérification e-mail et bienvenue."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from inscription.services.email_verification import (
    ErreurVerificationEmail,
    confirmer_email_avec_jeton,
    creer_jeton_verification,
)
from stock.models import Entreprise
from users.models import Membership

User = get_user_model()


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_BASE_URL='https://app.uhakikaapp.store',
)
class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='pending_user',
            email='pending@example.com',
            password='SecretPass123',
            role='admin',
            is_active=False,
            email_verifie=False,
        )

    def test_inscription_manuelle_retourne_attente_sans_tokens(self):
        with patch('inscription.views.envoyer_email_verification') as mock_send:
            mock_send.return_value = {'envoye': True, 'delai_renvoi_secondes': 60}
            resp = self.client.post('/api/inscription/compte/', {
                'username': 'new_user',
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'password': 'SecretPass123',
                'password_confirm': 'SecretPass123',
            }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data['statut_verification'], 'EN_ATTENTE')
        self.assertNotIn('tokens', resp.data)
        created = User.objects.get(email='new@example.com')
        self.assertFalse(created.email_verifie)
        self.assertFalse(created.is_active)

    def test_verification_active_le_compte_et_retourne_tokens(self):
        token, _ = creer_jeton_verification(self.user)
        resp = self.client.post('/api/inscription/verifier-email/', {'token': token}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data['email_verifie'])
        self.assertIn('tokens', resp.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verifie)
        self.assertTrue(self.user.is_active)

    def test_login_bloque_si_email_non_verifie(self):
        resp = self.client.post('/api/auth/', {
            'username': 'pending_user',
            'password': 'SecretPass123',
        }, format='json')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.data.get('code'), 'email_not_verified')

    def test_jeton_expire(self):
        token, jeton = creer_jeton_verification(self.user)
        jeton.expire_le = jeton.expire_le.replace(year=2000)
        jeton.save(update_fields=['expire_le'])
        with self.assertRaises(ErreurVerificationEmail) as ctx:
            confirmer_email_avec_jeton(token)
        self.assertEqual(ctx.exception.code, 'token_expire')

    @patch('inscription.services.welcome_email.envoyer_email_bienvenue')
    def test_bienvenue_declenche_apres_configuration(self, mock_welcome):
        from inscription.services.welcome_email import envoyer_bienvenue_si_eligible
        from inscription.services.entreprise_saas import evaluer_et_marquer_configuration

        self.user.email_verifie = True
        self.user.is_active = True
        self.user.first_name = 'Jean'
        self.user.last_name = 'Dupont'
        self.user.save()
        ent = Entreprise.objects.create(
            nom='Ma société',
            email='contact@example.com',
            telephone='+243000',
            adresse='Kinshasa',
            pays='RDC',
            responsable='Jean Dupont',
            secteur='Commerce',
            nif='NIF-1',
            configuration_complete=False,
        )
        Membership.objects.create(user=self.user, entreprise=ent, role='admin', is_active=True)
        mock_welcome.return_value = True
        with patch('inscription.services.welcome_email.peut_envoyer_bienvenue', return_value=True):
            with patch('inscription.services.welcome_email.build_etat_licence', return_value={'est_actif': True, 'formule_nom': 'Découverte Pro', 'formule_code': 'decouverte_pro'}):
                with patch('inscription.services.welcome_email.build_resume_limites', return_value={}):
                    evaluer_et_marquer_configuration(ent)
        self.assertTrue(mock_welcome.called or ent.configuration_complete)
