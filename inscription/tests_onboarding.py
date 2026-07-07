"""Tests parcours onboarding backend."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from abonnements.models import AbonnementEntreprise, FormuleAbonnement
from inscription.services.email_verification import creer_jeton_verification
from inscription.services.workspace_activation import creer_jeton_activation_espace
from stock.models import Entreprise
from users.models import Membership

User = get_user_model()


class OnboardingFlowTests(TestCase):
    def setUp(self):
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Découverte Pro', 'duree_essai_jours': 60},
        )
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='onboarduser',
            password='testpass123',
            role='admin',
            email='onboard@test.com',
            email_verifie=True,
        )

    def _auth(self):
        self.client.force_authenticate(user=self.user)

    def _creer_entreprise_provisoire(self):
        ent = Entreprise.objects.create(
            nom='Ma Boutique',
            email='shop@test.com',
            telephone='+243900000000',
            adresse='12 rue Test',
            pays='RDC',
            responsable='Jean Dupont',
            secteur='Commerce',
        )
        Membership.objects.create(user=self.user, entreprise=ent, role='admin', is_active=True)
        return ent

    def test_status_initial_profile_step(self):
        self._auth()
        resp = self.client.get('/api/onboarding/status/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['next_step'], 'profile')
        self.assertFalse(resp.data['onboarding_completed'])

    def test_patch_profile_advances_to_company(self):
        self._auth()
        self._creer_entreprise_provisoire()
        resp = self.client.patch('/api/onboarding/profile/', {
            'first_name': 'Jean',
            'last_name': 'Dupont',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['profile_completed'])
        self.assertEqual(resp.data['next_step'], 'company')

    def test_complete_onboarding_requires_company(self):
        self._auth()
        resp = self.client.post('/api/onboarding/complete/', {}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('title', resp.data)
        self.assertIn('detail', resp.data)

    @patch('inscription.services.onboarding_actions.envoyer_email_activation_espace', return_value=True)
    def test_full_onboarding_flow(self, _mock_email):
        self._auth()
        ent = self._creer_entreprise_provisoire()
        self.client.patch('/api/onboarding/profile/', {
            'first_name': 'Jean',
            'last_name': 'Dupont',
        }, format='json')
        self.client.patch('/api/onboarding/company/', {
            'nom': ent.nom,
            'email': ent.email,
            'telephone': ent.telephone,
            'adresse': ent.adresse,
            'pays': ent.pays,
            'responsable': ent.responsable,
            'secteur': ent.secteur,
        }, format='json')
        resp = self.client.post('/api/onboarding/complete/', {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['onboarding_completed'])
        self.assertEqual(resp.data['next_step'], 'activation')

        self.user.refresh_from_db()
        token, _ = creer_jeton_activation_espace(self.user)
        resp = self.client.post('/api/onboarding/activate-workspace/', {'token': token}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['onboarding']['workspace_activated'])

        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/onboarding/mark-welcome-seen/', {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['welcome_seen'])
        self.assertEqual(resp.data['next_step'], 'dashboard')

    def test_verify_email_redirects_to_onboarding(self):
        user = User.objects.create_user(
            username='newuser',
            password='testpass123',
            role='admin',
            email='new@test.com',
            is_active=False,
        )
        token, _ = creer_jeton_verification(user)
        resp = self.client.post('/api/inscription/verifier-email/', {'token': token}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('/onboarding', resp.data['redirection'])
        self.assertEqual(resp.data['next_step'], 'profile')

    def test_operations_blocked_before_onboarding_complete(self):
        self._auth()
        self._creer_entreprise_provisoire()
        from rest_framework_simplejwt.tokens import RefreshToken
        m = Membership.objects.get(user=self.user, is_active=True)
        refresh = RefreshToken.for_user(self.user)
        refresh['entreprise_id'] = m.entreprise_id
        refresh['membership_id'] = m.id
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        resp = self.client.post('/api/typearticles/', {'nom': 'X'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertIn('title', resp.json())
        self.assertIn('detail', resp.json())

    def test_flow_acces_dashboard_false_until_welcome(self):
        self._auth()
        self._creer_entreprise_provisoire()
        resp = self.client.get('/api/inscription/flow/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['acces_dashboard'])
