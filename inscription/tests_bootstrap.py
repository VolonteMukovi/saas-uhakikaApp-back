"""Tests bootstrap post-authentification."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from abonnements.models import AbonnementEntreprise, FormuleAbonnement
from inscription.models import ProfilConnexionGoogle
from users.models import Membership

User = get_user_model()

FAKE_GOOGLE_JWT = 'aaa.bbb.ccc'

PAYLOAD_GOOGLE = {
    'sub': 'google-bootstrap-001',
    'email': 'bootstrap@gmail.com',
    'email_verified': True,
    'given_name': 'Marie',
    'family_name': 'Curie',
    'picture': '',
    'iss': 'https://accounts.google.com',
}


class BootstrapSaasTests(TestCase):
    def setUp(self):
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Découverte Pro', 'duree_essai_jours': 60},
        )
        self.client = APIClient()

    def test_bootstrap_creer_contexte_utilisateur_sans_entreprise(self):
        user = User.objects.create_user(
            username='nobiz',
            password='testpass123',
            role='admin',
            email='nobiz@test.com',
        )
        self.client.force_authenticate(user=user)
        resp = self.client.post('/api/inscription/bootstrap/', {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['bootstrap']['bootstrap_effectue'])
        self.assertTrue(resp.data['a_entreprise'])
        self.assertTrue(resp.data['acces_dashboard'])
        self.assertTrue(resp.data['licence_active'])
        self.assertIn('tokens', resp.data)
        m = Membership.objects.get(user=user, is_active=True)
        abo = AbonnementEntreprise.objects.get(entreprise_id=m.entreprise_id, est_courant=True)
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_ESSAI)

    @patch('inscription.views.verifier_id_token_google')
    def test_google_nouveau_compte_bootstrap_automatique(self, mock_verify):
        mock_verify.return_value = PAYLOAD_GOOGLE
        resp = self.client.post('/api/inscription/google/', {
            'credential': FAKE_GOOGLE_JWT,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['est_nouveau_compte'])
        self.assertTrue(resp.data['a_entreprise'])
        self.assertIsNotNone(resp.data['entreprise_id'])
        self.assertEqual(resp.data['prochaine_etape'], 'utiliser_application')
        user = User.objects.get(email='bootstrap@gmail.com')
        self.assertTrue(Membership.objects.filter(user=user, is_active=True).exists())
        self.assertIn('bootstrap', resp.data)
        self.assertTrue(resp.data['bootstrap']['bootstrap_effectue'])

    def test_flow_bootstrap_utilisateur_incomplet(self):
        user = User.objects.create_user(
            username='flowboot',
            password='testpass123',
            role='admin',
            email='flowboot@test.com',
        )
        self.client.force_authenticate(user=user)
        resp = self.client.get('/api/inscription/flow/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['a_entreprise'])
        self.assertTrue(resp.data['licence_active'])
        self.assertIn('tokens', resp.data)

    def test_mon_abonnement_sans_abonnement_initialise_pas_expire(self):
        user = User.objects.create_user(
            username='licuser',
            password='testpass123',
            role='admin',
            email='lic@test.com',
        )
        self.client.force_authenticate(user=user)
        resp = self.client.get('/api/abonnements/mon-abonnement/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['statut'], AbonnementEntreprise.STATUT_ESSAI)
        self.assertTrue(resp.data['est_actif'])
