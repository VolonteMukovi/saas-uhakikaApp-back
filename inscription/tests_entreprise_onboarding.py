"""Tests entreprise onboarding sans duplication."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from abonnements.models import FormuleAbonnement
from inscription.services.bootstrap_saas import assurer_contexte_initial_utilisateur
from inscription.services.entreprise_saas import creer_entreprise_minimale
from stock.models import Entreprise
from users.models import Membership

User = get_user_model()


class EntrepriseOnboardingTests(TestCase):
    def setUp(self):
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Essai', 'duree_essai_jours': 60},
        )
        self.user = User.objects.create_user(
            username='onboard_user',
            email='onboard@test.com',
            password='SecretPass123',
            role='admin',
            email_verifie=True,
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_bootstrap_puis_entreprise_minimale_met_a_jour_sans_doublon(self):
        bootstrap = assurer_contexte_initial_utilisateur(self.user)
        self.assertTrue(bootstrap['bootstrap_effectue'])
        ent_id = bootstrap['entreprise_id']
        self.assertEqual(Entreprise.objects.filter(memberships__user=self.user).count(), 1)

        result = creer_entreprise_minimale(self.user, nom='hoko', pays='RDC')
        self.assertTrue(result['mis_a_jour'])
        self.assertEqual(result['entreprise_id'], ent_id)
        self.assertEqual(Entreprise.objects.filter(memberships__user=self.user).count(), 1)

        ent = Entreprise.objects.get(pk=ent_id)
        self.assertEqual(ent.nom, 'hoko')

    def test_post_entreprise_api_met_a_jour_provisoire(self):
        assurer_contexte_initial_utilisateur(self.user)
        resp = self.client.post('/api/entreprises/', {
            'nom': 'Nouvelle',
            'secteur': 'Commerce',
            'pays': 'RDC',
            'adresse': 'Kin',
            'telephone': '+243',
            'email': 'shop@test.com',
            'nif': 'NIF',
            'responsable': 'Boss',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data.get('mis_a_jour'))
        self.assertEqual(Entreprise.objects.filter(memberships__user=self.user).count(), 1)
        ent = Entreprise.objects.get(memberships__user=self.user)
        self.assertEqual(ent.nom, 'Nouvelle')

    def test_consolidation_supprime_doublon_provisoire(self):
        from inscription.services.entreprise_onboarding import consolider_entreprises_utilisateur

        bootstrap = assurer_contexte_initial_utilisateur(self.user)
        ent1_id = bootstrap['entreprise_id']
        ent2 = Entreprise.objects.create(
            nom='Doublon',
            secteur='À compléter',
            pays='RDC',
            adresse='À compléter',
            telephone='À compléter',
            email='dup@test.com',
            nif='À compléter',
            responsable='Test',
            configuration_complete=False,
        )
        Membership.objects.create(user=self.user, entreprise=ent2, role='admin', is_active=True)
        self.assertEqual(Membership.objects.filter(user=self.user, is_active=True).count(), 2)

        supprimees = consolider_entreprises_utilisateur(self.user)
        self.assertEqual(supprimees, 1)
        self.assertEqual(Membership.objects.filter(user=self.user, is_active=True).count(), 1)
        self.assertTrue(Membership.objects.filter(user=self.user, entreprise_id=ent1_id).exists())

    def test_entreprise_minimale_endpoint_met_a_jour(self):
        assurer_contexte_initial_utilisateur(self.user)
        ent_avant = Membership.objects.get(user=self.user, is_active=True).entreprise_id
        resp = self.client.post('/api/inscription/entreprise-minimale/', {
            'nom': 'Ma Boutique',
            'pays': 'RDC',
            'source_activation': 'essai_gratuit',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data.get('mis_a_jour'))
        self.assertEqual(resp.data['entreprise_id'], ent_avant)
        self.assertEqual(Entreprise.objects.filter(memberships__user=self.user).count(), 1)
