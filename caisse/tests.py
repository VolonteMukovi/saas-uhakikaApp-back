from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from caisse.models import MouvementCaisse, TypeCaisse
from stock.models import Client, ClientEntreprise, Devise, Entreprise, Sortie
from users.models import Membership


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class MultiDeviseConversionTests(APITestCase):
    """Conversion inter-devises : vente, mouvement caisse."""

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
