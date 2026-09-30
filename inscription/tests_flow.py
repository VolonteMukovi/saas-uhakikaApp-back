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

    def test_flow_expose_etat_onboarding(self):
        """Le frontend redirige à partir de ces champs : ils ne doivent pas être filtrés par le serializer."""
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/inscription/flow/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['onboarding_completed'])
        self.assertTrue(resp.data['workspace_activated'])
        self.assertTrue(resp.data['welcome_seen'])
        self.assertIn('next_step', resp.data)
        self.assertIn('redirection', resp.data)
        self.assertEqual(resp.data['onboarding']['next_step'], resp.data['next_step'])

    def test_flow_onboarding_non_finalise(self):
        self.user.onboarding_complete = False
        self.user.save(update_fields=['onboarding_complete'])
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/inscription/flow/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['onboarding_completed'])
        self.assertNotEqual(resp.data['next_step'], 'dashboard')

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
        # Onboarding terminé : dashboard accessible, mais opérations métier bloquées
        # tant que l'entreprise n'est pas configurée.
        self.assertTrue(resp.data['acces_dashboard'])
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
