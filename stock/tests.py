"""
Tests isolation multi-tenant (endpoints métier).
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from stock.models import Article, Devise, Entreprise, LigneEntree, Stock, SousTypeArticle, TypeArticle, Unite
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
class EntreeCreationNoDuplicateTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E2',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='e2@e.com',
            nif='n2',
            responsable='r2',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_entree',
            email='entree@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user,
            entreprise=self.entreprise,
            role='admin',
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

        self.unite = Unite.objects.create(libelle='pc', entreprise=self.entreprise)
        self.type_article = TypeArticle.objects.create(libelle='Boisson', entreprise=self.entreprise)
        self.sous_type = SousTypeArticle.objects.create(
            type_article=self.type_article,
            libelle='Thermos',
            entreprise=self.entreprise,
        )
        self.devise = Devise.objects.create(
            sigle='USD',
            nom='Dollar',
            symbole='$',
            est_principal=True,
            entreprise=self.entreprise,
        )
        self.articles = [
            Article.objects.create(
                nom_scientifique='thermos 3l',
                nom_commercial='thermos 3l',
                sous_type_article=self.sous_type,
                unite=self.unite,
                emplacement='A1',
                entreprise=self.entreprise,
            ),
            Article.objects.create(
                nom_scientifique='bolle plastique avec couvercle',
                nom_commercial='bolle plastique avec couvercle',
                sous_type_article=self.sous_type,
                unite=self.unite,
                emplacement='A2',
                entreprise=self.entreprise,
            ),
            Article.objects.create(
                nom_scientifique='gourde 0,5l',
                nom_commercial='gourde 0,5l',
                sous_type_article=self.sous_type,
                unite=self.unite,
                emplacement='A3',
                entreprise=self.entreprise,
            ),
        ]

    def test_create_entree_creates_each_line_once_and_updates_stock_once(self):
        payload = {
            'libele': 'Approvisionnement test',
            'description': 'Validation anti-doublon',
            'lignes': [
                {
                    'article_id': self.articles[0].pk,
                    'quantite': '1',
                    'prix_unitaire': '0',
                    'prix_vente': '12.5',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                },
                {
                    'article_id': self.articles[1].pk,
                    'quantite': '1',
                    'prix_unitaire': '0',
                    'prix_vente': '0.625',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                },
                {
                    'article_id': self.articles[2].pk,
                    'quantite': '3',
                    'prix_unitaire': '0',
                    'prix_vente': '4',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                },
            ],
        }

        response = self.client.post('/api/entrees/', payload, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(LigneEntree.objects.count(), 3)
        self.assertEqual(response.json()['articles_traites'], 3)

        qtes = {
            ligne.article_id: ligne.quantite
            for ligne in LigneEntree.objects.select_related('article')
        }
        self.assertEqual(qtes[self.articles[0].pk], Decimal('1'))
        self.assertEqual(qtes[self.articles[1].pk], Decimal('1'))
        self.assertEqual(qtes[self.articles[2].pk], Decimal('3'))

        stocks = {stock.article_id: stock.Qte for stock in Stock.objects.select_related('article')}
        self.assertEqual(stocks[self.articles[0].pk], Decimal('1'))
        self.assertEqual(stocks[self.articles[1].pk], Decimal('1'))
        self.assertEqual(stocks[self.articles[2].pk], Decimal('3'))

