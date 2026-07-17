from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from stock.models import (
    Article,
    Devise,
    Entree,
    Entreprise,
    InventaireLigne,
    InventaireSession,
    LigneEntree,
    Stock,
    SousTypeArticle,
    TypeArticle,
    Unite,
)
from users.models import Membership


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class InventaireValorisationTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-INV',
            secteur='s',
            pays='CD',
            adresse='a',
            telephone='t',
            email='inv@example.com',
            nif='n-inv',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_inv',
            email='inv@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user,
            entreprise=self.entreprise,
            role='admin',
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

        Devise.objects.create(
            sigle='USD', nom='Dollar', symbole='$',
            est_principal=True, entreprise=self.entreprise,
        )
        self.unite = Unite.objects.create(libelle='pcs', entreprise=self.entreprise)
        self.type_art = TypeArticle.objects.create(libelle='Produit', entreprise=self.entreprise)
        self.sous = SousTypeArticle.objects.create(
            libelle='Tomate', type_article=self.type_art, entreprise=self.entreprise,
        )
        self.article = Article.objects.create(
            nom_scientifique='Tomate',
            nom_commercial='Tomate fraîche',
            sous_type_article=self.sous,
            unite=self.unite,
            entreprise=self.entreprise,
        )
        Stock.objects.create(article=self.article, Qte=Decimal('152'), seuilAlert=Decimal('10'))
        entree = Entree.objects.create(libele='Appro', entreprise=self.entreprise)
        LigneEntree.objects.create(
            article=self.article,
            entree=entree,
            quantite=Decimal('200'),
            quantite_restante=Decimal('152'),
            prix_unitaire=Decimal('0.33000'),
            prix_vente=Decimal('0.50000'),
        )

    def test_demarrer_fige_pu_et_montants(self):
        create = self.client.post(
            '/api/inventaires/',
            {
                'libelle': 'Inventaire test',
                'date_inventaire': timezone.now().date().isoformat(),
                'perimetre': 'EN_STOCK',
                'demarrer': True,
            },
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.content)
        data = create.json()
        self.assertEqual(data['statut'], 'EN_COURS')
        self.assertGreaterEqual(len(data['lignes']), 1)
        ligne = next(l for l in data['lignes'] if l['article_id'] == self.article.article_id)
        self.assertEqual(ligne['dernier_prix_unitaire'], '0.33000')
        self.assertEqual(ligne['stock_theorique'], '152.00000')
        self.assertEqual(ligne['montant_logiciel'], '50.16000')
        self.assertIsNone(ligne['montant_physique'])
        self.assertEqual(data['resume']['capital_logiciel'], '50.16000')

        patch = self.client.patch(
            f"/api/inventaires/{data['id']}/lignes/{ligne['id']}/",
            {'stock_physique': '150'},
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        detail = self.client.get(f"/api/inventaires/{data['id']}/")
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        ligne2 = body['lignes'][0]
        self.assertEqual(ligne2['montant_physique'], '49.50000')
        self.assertEqual(ligne2['ecart_montant'], '-0.66000')
        self.assertEqual(body['resume']['capital_physique'], '49.50000')
        self.assertEqual(body['resume']['ecart_financier'], '-0.66000')
        self.assertEqual(body['resume']['capital_reel_stock'], '49.50000')
        self.assertEqual(body['resume']['total_ecart_montant'], '-0.66000')
        self.assertEqual(body['resume']['total_ecart_positif'], '0.00000')
        self.assertEqual(body['resume']['total_ecart_negatif'], '0.66000')

        # Le PU reste figé même si un nouvel appro arrive.
        entree2 = Entree.objects.create(libele='Appro 2', entreprise=self.entreprise)
        LigneEntree.objects.create(
            article=self.article,
            entree=entree2,
            quantite=Decimal('10'),
            quantite_restante=Decimal('10'),
            prix_unitaire=Decimal('9.99000'),
            prix_vente=Decimal('12.00000'),
        )
        detail2 = self.client.get(f"/api/inventaires/{data['id']}/")
        self.assertEqual(detail2.json()['lignes'][0]['dernier_prix_unitaire'], '0.33000')

    def test_sans_appro_pu_zero(self):
        art2 = Article.objects.create(
            nom_scientifique='Sans Appro',
            nom_commercial='Sans Appro',
            sous_type_article=self.sous,
            unite=self.unite,
            entreprise=self.entreprise,
        )
        Stock.objects.create(article=art2, Qte=Decimal('5'), seuilAlert=Decimal('1'))
        create = self.client.post(
            '/api/inventaires/',
            {
                'libelle': 'Inv sans prix',
                'date_inventaire': timezone.now().date().isoformat(),
                'perimetre': 'PARTIEL',
                'article_ids': [art2.article_id],
                'demarrer': True,
            },
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.content)
        ligne = create.json()['lignes'][0]
        self.assertEqual(ligne['dernier_prix_unitaire'], '0.00000')
        self.assertEqual(ligne['montant_logiciel'], '0.00000')

    def test_totaux_ecarts_positifs_et_negatifs(self):
        art_surplus = Article.objects.create(
            nom_scientifique='Oignon',
            nom_commercial='Oignon',
            sous_type_article=self.sous,
            unite=self.unite,
            entreprise=self.entreprise,
        )
        Stock.objects.create(article=art_surplus, Qte=Decimal('10'), seuilAlert=Decimal('2'))
        entree = Entree.objects.create(libele='Appro oignon', entreprise=self.entreprise)
        LigneEntree.objects.create(
            article=art_surplus,
            entree=entree,
            quantite=Decimal('20'),
            quantite_restante=Decimal('10'),
            prix_unitaire=Decimal('3.00000'),
            prix_vente=Decimal('4.00000'),
        )

        create = self.client.post(
            '/api/inventaires/',
            {
                'libelle': 'Inv écarts ±',
                'date_inventaire': timezone.now().date().isoformat(),
                'perimetre': 'PARTIEL',
                'article_ids': [self.article.article_id, art_surplus.article_id],
                'demarrer': True,
            },
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.content)
        inv_id = create.json()['id']
        lignes = {l['article_id']: l for l in create.json()['lignes']}

        # Tomate : 152 → 150 → écart montant -0.66
        self.client.patch(
            f"/api/inventaires/{inv_id}/lignes/{lignes[self.article.article_id]['id']}/",
            {'stock_physique': '150'},
            format='json',
        )
        # Oignon : 10 → 14 → écart montant +12
        self.client.patch(
            f"/api/inventaires/{inv_id}/lignes/{lignes[art_surplus.article_id]['id']}/",
            {'stock_physique': '14'},
            format='json',
        )

        detail = self.client.get(f'/api/inventaires/{inv_id}/').json()
        by_id = {l['article_id']: l for l in detail['lignes']}
        self.assertEqual(by_id[self.article.article_id]['ecart_montant'], '-0.66000')
        self.assertEqual(by_id[art_surplus.article_id]['ecart_montant'], '12.00000')

        resume = detail['resume']
        self.assertEqual(resume['total_ecart_positif'], '12.00000')
        self.assertEqual(resume['total_ecart_negatif'], '0.66000')
        self.assertEqual(resume['total_ecart_montant'], '11.34000')
