"""
Non-régression : isolation entre entreprises sur les ventes et génération des codes article.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from caisse.models import TypeCaisse
from stock.models import (
    Article,
    Devise,
    Entree,
    Entreprise,
    LigneEntree,
    Sortie,
    SousTypeArticle,
    Stock,
    TypeArticle,
    Unite,
)
from users.models import Membership


def _creer_entreprise(suffixe):
    entreprise = Entreprise.objects.create(
        nom=f'E-{suffixe}',
        secteur='s',
        pays='CD',
        adresse='a',
        telephone='t',
        email=f'{suffixe}@example.com',
        nif=f'nif-{suffixe}',
        responsable='resp',
    )
    devise = Devise.objects.create(
        sigle='USD', nom='Dollar', symbole='$', est_principal=True, entreprise=entreprise,
    )
    type_caisse = TypeCaisse.objects.create(
        nom=f'Caisse {suffixe}',
        libelle=f'Caisse {suffixe}',
        code_type='BANQUE',
        entreprise=entreprise,
        devise=devise,
        is_active=True,
    )
    unite = Unite.objects.create(libelle='pc', entreprise=entreprise)
    type_article = TypeArticle.objects.create(libelle='Divers', entreprise=entreprise)
    sous_type = SousTypeArticle.objects.create(
        type_article=type_article, libelle='General', entreprise=entreprise,
    )
    return entreprise, devise, type_caisse, unite, sous_type


def _creer_article_avec_stock(entreprise, devise, unite, sous_type, nom, quantite='10'):
    article = Article.objects.create(
        nom_scientifique=nom,
        nom_commercial=nom,
        sous_type_article=sous_type,
        unite=unite,
        emplacement='A1',
        entreprise=entreprise,
    )
    entree = Entree.objects.create(libele='Appro', entreprise=entreprise)
    LigneEntree.objects.create(
        article=article,
        entree=entree,
        quantite=Decimal(quantite),
        quantite_restante=Decimal(quantite),
        prix_unitaire=Decimal('2'),
        prix_vente=Decimal('10'),
        devise=devise,
        seuil_alerte=Decimal('0'),
    )
    Stock.objects.update_or_create(
        article=article, defaults={'Qte': Decimal(quantite), 'seuilAlert': Decimal('0')},
    )
    return article


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class ArticleIdGlobalTests(APITestCase):
    def test_deux_entreprises_meme_prefixe_codes_distincts_sans_ecrasement(self):
        ent_a, _dev_a, _tc_a, unite_a, st_a = _creer_entreprise('a')
        ent_b, _dev_b, _tc_b, unite_b, st_b = _creer_entreprise('b')

        article_a = Article.objects.create(
            nom_scientifique='produit A', sous_type_article=st_a, unite=unite_a, entreprise=ent_a,
        )
        article_b = Article(
            nom_scientifique='produit B', sous_type_article=st_b, unite=unite_b, entreprise=ent_b,
        )
        article_b.save()

        self.assertEqual(article_a.article_id[:4], article_b.article_id[:4])
        self.assertNotEqual(article_a.article_id, article_b.article_id)
        article_a.refresh_from_db()
        self.assertEqual(article_a.nom_scientifique, 'produit A')
        self.assertEqual(article_a.entreprise_id, ent_a.pk)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class VenteIsolationTenantTests(APITestCase):
    def setUp(self):
        self.ent_a, self.devise_a, self.caisse_a, unite_a, st_a = _creer_entreprise('vente-a')
        self.ent_b, self.devise_b, _caisse_b, unite_b, st_b = _creer_entreprise('vente-b')
        self.article_a = _creer_article_avec_stock(self.ent_a, self.devise_a, unite_a, st_a, 'article A')
        self.article_b = _creer_article_avec_stock(self.ent_b, self.devise_b, unite_b, st_b, 'article B')

        user = get_user_model().objects.create_user(
            username='agent_a', email='agent_a@example.com', password='secretpass123',
        )
        Membership.objects.create(user=user, entreprise=self.ent_a, role='admin', is_active=True)
        self.client.force_authenticate(user=user)

    def _vendre(self, article, devise):
        return self.client.post('/api/sorties/', {
            'statut': 'PAYEE',
            'type_caisse_id': self.caisse_a.pk,
            'lignes': [{
                'article_id': article.pk,
                'quantite': '2',
                'prix_unitaire': '10',
                'devise_id': devise.pk,
            }],
        }, format='json')

    def test_vente_article_propre_entreprise_decremente_lot_et_stock(self):
        response = self._vendre(self.article_a, self.devise_a)
        self.assertEqual(response.status_code, 201, response.content)
        lot = LigneEntree.objects.get(article=self.article_a)
        self.assertEqual(lot.quantite_restante, Decimal('8'))
        self.assertEqual(Stock.objects.get(article=self.article_a).Qte, Decimal('8'))

    def test_vente_article_autre_entreprise_refusee(self):
        response = self._vendre(self.article_b, self.devise_a)
        self.assertEqual(response.status_code, 400, response.content)
        lot_b = LigneEntree.objects.get(article=self.article_b)
        self.assertEqual(lot_b.quantite_restante, Decimal('10'))
        self.assertFalse(Sortie.objects.filter(entreprise=self.ent_a).exists())

    def test_vente_devise_autre_entreprise_refusee(self):
        response = self._vendre(self.article_a, self.devise_b)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            LigneEntree.objects.get(article=self.article_a).quantite_restante, Decimal('10'),
        )
