"""
Tests isolation multi-tenant (endpoints métier).
"""
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from caisse.services.caisse import creer_mouvement_caisse
from stock.models import Client, Devise, DetteClient, Entreprise, Sortie
from users.models import Membership


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class BeneficesTotauxTenantTests(APITestCase):
    """GET /api/entrees/benefices-totaux/ est borné à l'entreprise du membership."""

    def test_benefices_totaux_details_entreprise_id_du_membership(self):
        ent = Entreprise.objects.create(
            nom='E1',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='e@e.com',
            nif='n',
            responsable='r',
        )
        User = get_user_model()
        user = User.objects.create_user(
            username='admin_bt',
            email='a@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=user, entreprise=ent, role='admin', is_active=True,
        )
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/entrees/benefices-totaux/', {'year': 2026, 'month': 3})
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['details']['entreprise_id'], ent.id)
        # Pas de succursale dans le JWT → filtre entreprise seule
        self.assertIsNone(data['details']['succursale_id'])


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class TauxChangeApiTests(APITestCase):
    def setUp(self):
        self.ent = Entreprise.objects.create(
            nom='E2',
            secteur='s',
            pays='CD',
            adresse='a',
            telephone='t',
            email='e2@e.com',
            nif='n2',
            responsable='r2',
        )
        self.usd = Devise.objects.create(
            sigle='USD',
            nom='Dollar americain',
            symbole='$',
            est_principal=True,
            entreprise=self.ent,
        )
        self.cdf = Devise.objects.create(
            sigle='CDF',
            nom='Franc congolais',
            symbole='FC',
            entreprise=self.ent,
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_fx',
            email='fx@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user, entreprise=self.ent, role='admin', is_active=True,
        )
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/taux-change/', {
            'source_devise_id': self.usd.id,
            'target_devise_id': self.cdf.id,
            'taux': '2800',
            'date_application': '2026-06-01T08:00:00Z',
        }, format='json')

    def test_create_taux_change_endpoint(self):
        response = self.client.post('/api/taux-change/', {
            'source_devise_id': self.usd.id,
            'target_devise_id': self.cdf.id,
            'taux': '2800',
            'date_application': '2026-06-28T08:14:00Z',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data['source_devise']['sigle'], 'USD')
        self.assertEqual(data['target_devise']['sigle'], 'CDF')
        self.assertEqual(data['taux'], '2800')

    def test_list_taux_change_endpoint_returns_latest_active_rate_by_pair(self):
        self.client.post('/api/taux-change/', {
            'source_devise_id': self.usd.id,
            'target_devise_id': self.cdf.id,
            'taux': '2800',
            'date_application': '2026-06-22T08:00:00Z',
        }, format='json')
        self.client.post('/api/taux-change/', {
            'source_devise_id': self.usd.id,
            'target_devise_id': self.cdf.id,
            'taux': '2850',
            'date_application': '2026-06-25T08:00:00Z',
        }, format='json')

        response = self.client.get('/api/taux-change/')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['taux'], '2850')

    def test_creer_mouvement_caisse_stores_snapshot_reference(self):
        mouvement = creer_mouvement_caisse(
            montant='28000.00000',
            devise=self.cdf,
            type_mouvement='ENTREE',
            entreprise_id=self.ent.id,
            succursale_id=None,
            motif='Test snapshot devise',
            skip_session_check=True,
        )
        self.assertIsNotNone(mouvement.devise_reference_id)
        self.assertIsNotNone(mouvement.taux_change)
        self.assertGreater(mouvement.montant_reference, 0)
        self.assertEqual(mouvement.devise_reference_id, self.usd.id)

    def test_create_dette_endpoint_sets_currency_snapshot(self):
        client = Client.objects.create(id='CLI-FX-1', nom='Client FX')
        sortie = Sortie.objects.create(
            client=client,
            devise=self.cdf,
            statut='EN_CREDIT',
            entreprise=self.ent,
        )
        resp = self.client.post('/api/dettes/', {
            'client_id': client.id,
            'sortie_id': sortie.id,
            'montant_total': '28000.00000',
            'devise_id': self.cdf.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        dette = DetteClient.objects.get(sortie=sortie)
        self.assertEqual(dette.devise_id, self.cdf.id)
        self.assertEqual(dette.devise_reference_id, self.usd.id)
        self.assertIsNotNone(dette.taux_change)
        self.assertGreater(dette.montant_reference, 0)
