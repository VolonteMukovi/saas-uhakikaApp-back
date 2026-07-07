"""Tests flow SaaS frontend."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from abonnements.models import AbonnementEntreprise, FormuleAbonnement

User = get_user_model()


class FlowSaasTests(TestCase):
    def setUp(self):
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Essai', 'duree_essai_jours': 60},
        )
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='flowuser',
            password='testpass123',
            role='admin',
            email='flow@test.com',
            email_verifie=True,
            first_name='Flow',
            last_name='User',
            onboarding_complete=True,
            workspace_activated=True,
            welcome_seen=True,
        )

    def test_flow_sans_entreprise_bootstrap_auto(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/inscription/flow/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['a_entreprise'])
        self.assertTrue(resp.data['acces_dashboard'])
        self.assertTrue(resp.data['licence_active'])
        self.assertIn('tokens', resp.data)

    def test_creer_entreprise_minimale_essai(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/inscription/entreprise-minimale/', {
            'nom': 'Ma Boutique',
            'pays': 'RDC',
            'formule_code': 'essai_gratuit',
            'periode': 'essai',
            'source_activation': 'essai_gratuit',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.data['acces_dashboard'])
        self.assertFalse(resp.data['configuration_entreprise_complete'])
        self.assertFalse(resp.data['operations_metier_autorisees'])
        self.assertIn('tokens', resp.data)

    def test_operations_bloquees_config_incomplete(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/inscription/entreprise-minimale/', {
            'nom': 'Shop',
            'pays': 'RDC',
            'source_activation': 'essai_gratuit',
        }, format='json')
        from rest_framework_simplejwt.tokens import RefreshToken
        from users.models import Membership
        m = Membership.objects.get(user=self.user, is_active=True)
        refresh = RefreshToken.for_user(self.user)
        refresh['entreprise_id'] = m.entreprise_id
        refresh['membership_id'] = m.id
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        resp = self.client.post('/api/typearticles/', {'nom': 'X'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get('code'), 'configuration_incomplete')
