from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from caisse.models import MouvementCaisse, TypeCaisse
from stock.models import Client, ClientEntreprise, Devise, DetteClient, Entreprise, Sortie
from users.models import Membership


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class PaiementDetteGroupedApiTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-Caisse',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='caisse@example.com',
            nif='n-caisse',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_caisse',
            email='admin-caisse@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user,
            entreprise=self.entreprise,
            role='admin',
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

        self.devise = Devise.objects.create(
            sigle='USD',
            nom='Dollar',
            symbole='$',
            est_principal=True,
            entreprise=self.entreprise,
        )
        self.type_caisse = TypeCaisse.objects.create(
            nom='Banque USD',
            libelle='Banque USD',
            code_type='BANQUE',
            entreprise=self.entreprise,
            devise=self.devise,
            is_active=True,
            est_defaut=False,
        )

        self.client_fiche = Client.objects.create(id='CLI0044', nom='JUSTIN MANDEFU')
        ClientEntreprise.objects.create(
            client=self.client_fiche,
            entreprise=self.entreprise,
        )

    def _create_dette(self, montant, *, client=None):
        target_client = client or self.client_fiche
        sortie = Sortie.objects.create(
            client=target_client,
            devise=self.devise,
            statut='EN_CREDIT',
            entreprise=self.entreprise,
        )
        return DetteClient.objects.create(
            client=target_client,
            sortie=sortie,
            montant_total=Decimal(str(montant)),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal(str(montant)),
            entreprise=self.entreprise,
            statut='EN_COURS',
        )

    def test_grouped_payment_can_pay_selected_debts_with_common_reference(self):
        dette_1 = self._create_dette('6.09000')
        dette_2 = self._create_dette('4.50000')
        self._create_dette('2.00000')

        response = self.client.post(
            '/api/paiements-dettes/grouped/',
            {
                'client_id': self.client_fiche.pk,
                'montant_paye': '10.59000',
                'devise_id': self.devise.pk,
                'type_caisse_id': self.type_caisse.pk,
                'dettes': [dette_1.pk, dette_2.pk],
                'mode_repartition': 'ANCIENNES_DETTES_D_ABORD',
                'commentaire': 'Paiement groupe test',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['client']['id'], self.client_fiche.pk)
        self.assertEqual(payload['paiement']['nombre_dettes_selectionnees'], 2)
        self.assertEqual(payload['paiement']['devise'], 'USD')
        self.assertEqual(len(payload['dettes_payees']), 2)

        dette_1.refresh_from_db()
        dette_2.refresh_from_db()
        self.assertEqual(dette_1.solde_restant, Decimal('0.00000'))
        self.assertEqual(dette_2.solde_restant, Decimal('0.00000'))
        self.assertEqual(dette_1.statut, 'PAYEE')
        self.assertEqual(dette_2.statut, 'PAYEE')

        mouvements = list(
            MouvementCaisse.objects.filter(reference_piece=payload['paiement']['reference']).order_by('id')
        )
        self.assertEqual(len(mouvements), 2)
        self.assertEqual(mouvements[0].montant, Decimal('6.09000'))
        self.assertEqual(mouvements[1].montant, Decimal('4.50000'))

    def test_grouped_payment_can_pay_all_and_allocate_oldest_debts_first(self):
        dette_1 = self._create_dette('6.09000')
        dette_2 = self._create_dette('4.50000')
        dette_3 = self._create_dette('2.00000')

        response = self.client.post(
            '/api/paiements-dettes/grouped/',
            {
                'client_id': self.client_fiche.pk,
                'montant_paye': '8.00000',
                'devise_id': self.devise.pk,
                'type_caisse_id': self.type_caisse.pk,
                'payer_toutes': True,
                'mode_repartition': 'ANCIENNES_DETTES_D_ABORD',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertEqual(payload['paiement']['nombre_dettes_selectionnees'], 3)
        self.assertEqual(len(payload['dettes_payees']), 2)

        dette_1.refresh_from_db()
        dette_2.refresh_from_db()
        dette_3.refresh_from_db()
        self.assertEqual(dette_1.solde_restant, Decimal('0.00000'))
        self.assertEqual(dette_2.solde_restant, Decimal('2.59000'))
        self.assertEqual(dette_3.solde_restant, Decimal('2.00000'))
        self.assertEqual(dette_1.statut, 'PAYEE')
        self.assertEqual(dette_2.statut, 'EN_COURS')
        self.assertEqual(dette_3.statut, 'EN_COURS')

        applied = payload['dettes_payees']
        self.assertEqual(applied[0]['dette_id'], dette_1.pk)
        self.assertEqual(Decimal(applied[0]['montant_applique']), Decimal('6.09000'))
        self.assertEqual(applied[1]['dette_id'], dette_2.pk)
        self.assertEqual(Decimal(applied[1]['montant_applique']), Decimal('1.91000'))
