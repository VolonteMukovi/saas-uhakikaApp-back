from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
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


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class MultiDeviseConversionTests(APITestCase):
    """Conversion inter-devises : vente, mouvement caisse, paiement dette."""

    def setUp(self):
        from stock.models import TauxChange

        self.TauxChange = TauxChange
        self.entreprise = Entreprise.objects.create(
            nom='E-FX',
            secteur='s',
            pays='CD',
            adresse='a',
            telephone='t',
            email='fx@example.com',
            nif='n-fx',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_fx',
            email='fx@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user,
            entreprise=self.entreprise,
            role='admin',
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

        self.usd = Devise.objects.create(
            sigle='USD', nom='Dollar', symbole='$', est_principal=True, entreprise=self.entreprise,
        )
        self.cdf = Devise.objects.create(
            sigle='CDF', nom='Franc congolais', symbole='FC', est_principal=False, entreprise=self.entreprise,
        )
        self.caisse_usd = TypeCaisse.objects.create(
            nom='Caisse USD', libelle='Caisse USD', code_type='CASH',
            entreprise=self.entreprise, devise=self.usd, is_active=True, est_defaut=True,
        )
        self.caisse_cdf = TypeCaisse.objects.create(
            nom='Caisse CDF', libelle='Caisse CDF', code_type='CASH',
            entreprise=self.entreprise, devise=self.cdf, is_active=True, est_defaut=False,
        )
        self.TauxChange.objects.create(
            entreprise=self.entreprise,
            devise_source=self.usd,
            devise_cible=self.cdf,
            taux=Decimal('2300'),
            is_active=True,
        )

    def test_preview_conversion_cdf_to_usd_caisse(self):
        response = self.client.post(
            '/api/mouvements-caisse/preview-conversion/',
            {
                'montant': '230000',
                'devise_id': self.cdf.pk,
                'type_caisse_id': self.caisse_usd.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data['conversion_appliquee'])
        self.assertEqual(data['montant_caisse'], '100.00000')
        self.assertEqual(data['devise_caisse']['sigle'], 'USD')
        self.assertEqual(data['devise_operation']['sigle'], 'CDF')

    def test_creer_mouvement_entree_cdf_dans_caisse_usd(self):
        from caisse.services.caisse import creer_mouvement_caisse

        mv = creer_mouvement_caisse(
            montant='230000',
            devise=self.cdf,
            type_mouvement='ENTREE',
            entreprise_id=self.entreprise.pk,
            succursale_id=None,
            motif='Test conversion',
            type_caisse=self.caisse_usd,
            skip_session_check=True,
        )
        self.assertEqual(mv.montant, Decimal('100.00000'))
        self.assertEqual(mv.devise_id, self.usd.pk)
        self.assertEqual(mv.montant_origine, Decimal('230000.00000'))
        self.assertEqual(mv.devise_origine_id, self.cdf.pk)
        self.assertIsNotNone(mv.taux_conversion)

    def test_paiement_dette_cdf_pour_dette_usd(self):
        client_fiche = Client.objects.create(id='CLI-FX-2', nom='Client FX')
        sortie = Sortie.objects.create(
            client=client_fiche, devise=self.usd, statut='EN_CREDIT', entreprise=self.entreprise,
        )
        dette = DetteClient.objects.create(
            client=client_fiche,
            sortie=sortie,
            montant_total=Decimal('1000.00000'),
            devise=self.usd,
            devise_reference=self.usd,
            montant_reference=Decimal('1000.00000'),
            entreprise=self.entreprise,
            statut='EN_COURS',
        )

        preview = self.client.post(
            '/api/paiements-dettes/preview/',
            {
                'dette_id': dette.pk,
                'montant_paye': '2300000',
                'devise_id': self.cdf.pk,
                'type_caisse_id': self.caisse_cdf.pk,
            },
            format='json',
        )
        self.assertEqual(preview.status_code, 200, preview.content)
        preview_data = preview.json()
        self.assertEqual(preview_data['dette']['equivalent_regle'], '1000.00000')
        self.assertEqual(Decimal(str(preview_data['dette']['solde_apres'])), Decimal('0'))

        response = self.client.post(
            '/api/paiements-dettes/',
            {
                'dette_id': dette.pk,
                'montant_paye': '2300000',
                'devise_id': self.cdf.pk,
                'type_caisse_id': self.caisse_cdf.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        dette.refresh_from_db()
        self.assertEqual(dette.solde_restant, Decimal('0.00000'))

    def test_preview_conversion_refuse_sans_taux(self):
        eur = Devise.objects.create(
            sigle='EUR', nom='Euro', symbole='€', est_principal=False, entreprise=self.entreprise,
        )
        response = self.client.post(
            '/api/mouvements-caisse/preview-conversion/',
            {
                'montant': '100',
                'devise_id': eur.pk,
                'type_caisse_id': self.caisse_usd.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_preview_conversion_via_taux_config_inverse_date_jour(self):
        """Taux UI (config) USD→CDF, date seule « demain » UTC + ids string → CDF→USD ok."""
        from datetime import timedelta

        self.TauxChange.objects.all().delete()
        demain = (timezone.now().date() + timedelta(days=1)).isoformat()
        self.entreprise.merge_config({
            'integrations': {
                'exchange_rates': [{
                    'id': 1,
                    'source_devise_id': str(self.usd.pk),
                    'target_devise_id': str(self.cdf.pk),
                    'rate': '2300',
                    'effective_at': demain,
                    'is_active': True,
                    'created_at': timezone.now().isoformat(),
                }],
            },
        })
        self.entreprise.save(update_fields=['config'])

        response = self.client.post(
            '/api/mouvements-caisse/preview-conversion/',
            {
                'montant': '230000',
                'devise_id': self.cdf.pk,
                'type_caisse_id': self.caisse_usd.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data['conversion_appliquee'])
        self.assertEqual(data['montant_caisse'], '100.00000')
