"""Tests paiement en ligne — étape 5."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from abonnements.models import AbonnementEntreprise, FormuleAbonnement, PaiementAbonnement
from abonnements.services.paiement import traiter_webhook_paiement
from stock.models import Entreprise

User = get_user_model()


@override_settings(PAIEMENT_GATEWAY_SANDBOX=True)
class PaiementEnLigneTests(TestCase):
    def setUp(self):
        from users.models import Membership
        from rest_framework_simplejwt.tokens import RefreshToken

        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Essai', 'duree_essai_jours': 60},
        )
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_STANDARD,
            defaults={
                'nom': 'Standard',
                'prix_mensuel': 35,
                'prix_annuel': 350,
                'est_visible_catalogue': True,
            },
        )
        self.user = User.objects.create_user(username='payuser', password='testpass123', role='admin')
        self.super = User.objects.create_superuser(username='superpay', password='superpass', email='s@p.com')
        self.ent = Entreprise.objects.create(nom='Pay Test')
        self.membership = Membership.objects.create(
            user=self.user, entreprise=self.ent, role='admin', is_active=True,
        )
        refresh = RefreshToken.for_user(self.user)
        refresh['entreprise_id'] = self.ent.id
        refresh['membership_id'] = self.membership.id
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_liste_fournisseurs(self):
        resp = self.client.get('/api/abonnements/paiements/fournisseurs/')
        self.assertEqual(resp.status_code, 200)
        codes = [f['code'] for f in resp.data['fournisseurs']]
        self.assertIn('maisha_pay', codes)

    def test_initier_paiement_sandbox(self):
        resp = self.client.post('/api/abonnements/paiements/initier/', {
            'formule_code': FormuleAbonnement.CODE_STANDARD,
            'periode': 'mensuel',
            'fournisseur': PaiementAbonnement.FOURNISSEUR_MAISHAPAY,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data.get('sandbox'))
        self.assertIn('reference_interne', resp.data)
        abo = AbonnementEntreprise.objects.get(entreprise=self.ent, est_courant=True)
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_EN_ATTENTE)

    def test_webhook_confirme_active_licence(self):
        init = self.client.post('/api/abonnements/paiements/initier/', {
            'formule_code': FormuleAbonnement.CODE_STANDARD,
            'periode': 'mensuel',
            'fournisseur': PaiementAbonnement.FOURNISSEUR_FLEXPAY,
        }, format='json')
        ref = init.data['reference_interne']
        paiement = PaiementAbonnement.objects.get(reference_interne=ref)
        result = traiter_webhook_paiement('flexpay', {
            'reference_interne': ref,
            'reference_externe': 'TX-123',
            'status': 'success',
            'amount': str(paiement.montant),
            'currency': paiement.devise,
        })
        self.assertEqual(result['statut'], 'confirme')
        paiement.refresh_from_db()
        abo = paiement.abonnement
        abo.refresh_from_db()
        self.assertEqual(paiement.statut, PaiementAbonnement.STATUT_CONFIRME)
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_ACTIF)
        self.assertTrue(abo.est_actif)

    def test_webhook_idempotent(self):
        init = self.client.post('/api/abonnements/paiements/initier/', {
            'formule_code': FormuleAbonnement.CODE_STANDARD,
            'periode': 'mensuel',
            'fournisseur': PaiementAbonnement.FOURNISSEUR_SERDI,
        }, format='json')
        ref = init.data['reference_interne']
        paiement = PaiementAbonnement.objects.get(reference_interne=ref)
        payload = {
            'reference_interne': ref,
            'order_id': ref,
            'payment_id': 'P1',
            'event': 'payment.success',
            'amount': str(paiement.montant),
            'currency': paiement.devise,
        }
        traiter_webhook_paiement('serdinate_pay', payload)
        result2 = traiter_webhook_paiement('serdinate_pay', payload)
        self.assertEqual(result2['statut'], 'deja_confirme')

    def test_statut_paiement_endpoint(self):
        init = self.client.post('/api/abonnements/paiements/initier/', {
            'formule_code': FormuleAbonnement.CODE_STANDARD,
            'periode': 'annuel',
            'fournisseur': PaiementAbonnement.FOURNISSEUR_MAISHAPAY,
        }, format='json')
        ref = init.data['reference_interne']
        resp = self.client.get(f'/api/abonnements/paiements/statut/{ref}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['reference_interne'], ref)
