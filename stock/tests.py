"""
Tests isolation multi-tenant (endpoints m├⌐tier).
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from django.utils import timezone

from caisse.models import MouvementCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse
from stock.models import (
    Article,
    ConditionnementArticle,
    Client,
    ClientEntreprise,
    Devise,
    Entreprise,
    Entree,
    LigneEntree,
    LigneSortie,
    PrixConditionnementEntree,
    Sortie,
    Stock,
    SousTypeArticle,
    TypeArticle,
    Unite,
)
from users.models import Membership

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class BeneficesTotauxTenantTests(APITestCase):
    """GET /api/entrees/benefices-totaux/ est born├⌐ ├á l'entreprise du membership."""

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
        # Pas de succursale dans le JWT ΓåÆ filtre entreprise seule
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

    def test_create_entree_ne_cree_pas_mouvement_caisse(self):
        """Un approvisionnement ne doit plus impacter la caisse automatiquement."""
        payload = {
            'libele': 'Appro cash decouple',
            'description': 'Test sans caisse',
            'lignes': [
                {
                    'article_id': self.articles[0].pk,
                    'quantite': '10',
                    'prix_unitaire': '25.5',
                    'prix_vente': '30',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                },
            ],
        }
        response = self.client.post('/api/entrees/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        entree_id = response.json()['id']
        self.assertEqual(
            MouvementCaisse.objects.filter(entree_id=entree_id).count(),
            0,
        )

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class ClientLifecycleApiTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-Client',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='client@example.com',
            nif='n-client',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_client',
            email='admin-client@example.com',
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
        self.unite = Unite.objects.create(libelle='pc', entreprise=self.entreprise)
        self.type_article = TypeArticle.objects.create(libelle='Divers', entreprise=self.entreprise)
        self.sous_type = SousTypeArticle.objects.create(
            type_article=self.type_article,
            libelle='General',
            entreprise=self.entreprise,
        )
        self.article = Article.objects.create(
            nom_scientifique='produit client',
            nom_commercial='produit client',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='A1',
            entreprise=self.entreprise,
        )
        self.client_fiche = Client.objects.create(id='CLI0099', nom='Client Test')
        ClientEntreprise.objects.create(client=self.client_fiche, entreprise=self.entreprise)
        entree = Entree.objects.create(libele='Appro lifecycle', entreprise=self.entreprise)
        LigneEntree.objects.create(
            article=self.article,
            entree=entree,
            quantite=Decimal('500'),
            quantite_restante=Decimal('500'),
            prix_unitaire=Decimal('5'),
            prix_vente=Decimal('10'),
            devise=self.devise,
            seuil_alerte=Decimal('0'),
        )
        Stock.objects.update_or_create(
            article=self.article,
            defaults={'Qte': Decimal('500'), 'seuilAlert': Decimal('0')},
        )

    def _add_line(self, sortie, quantite, prix_unitaire):
        return LigneSortie.objects.create(
            sortie=sortie,
            article=self.article,
            quantite=Decimal(str(quantite)),
            prix_unitaire=Decimal(str(prix_unitaire)),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal(str(quantite)) * Decimal(str(prix_unitaire)),
        )

    def _creer_sortie(self, *, statut='PAYEE', quantite='1', prix='10'):
        payload = {
            'statut': statut,
            'client_id': self.client_fiche.pk,
            'lignes': [{
                'article_id': self.article.pk,
                'quantite': quantite,
                'prix_unitaire': prix,
                'devise_id': self.devise.pk,
            }],
        }
        if statut == 'PAYEE':
            payload['type_caisse_id'] = self.type_caisse.pk
        response = self.client.post('/api/sorties/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_en_credit_sortie_creates_dette(self):
        response_data = self._creer_sortie(statut='EN_CREDIT', quantite='1', prix='10')
        sortie = Sortie.objects.get(pk=response_data['id'])
        self.assertEqual(sortie.statut, 'EN_CREDIT')
        from stock.models import DettesClients
        dette = DettesClients.objects.get(sortie=sortie)
        self.assertEqual(dette.montant, Decimal('10.00000'))
        self.assertEqual(dette.paye, Decimal('0.00000'))
        self.assertEqual(dette.reste, Decimal('10.00000'))
        self.assertEqual(dette.status, DettesClients.STATUS_ENCOURS)

    def test_dashboard_client_sans_achat(self):
        response = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['nombre_achats'], 0)
        self.assertEqual(data['total_achete'], '0.00000')
        self.assertEqual(data['dette_restante'], '0.00000')
        self.assertEqual(data['produits_achetes'], [])
        self.assertEqual(data['client']['type'], 'STANDARD')
        self.assertNotIn('chiffre_affaires_total', data)
        self.assertNotIn('resume', data)
        self.assertNotIn('repartition', data)

    def test_dashboard_achat_comptant(self):
        self._creer_sortie(statut='PAYEE', quantite='2', prix='25')
        data = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/').json()
        self.assertEqual(data['nombre_achats'], 1)
        self.assertEqual(data['total_achete'], '50.00000')
        self.assertEqual(data['dette_restante'], '0.00000')
        self.assertEqual(len(data['produits_achetes']), 1)
        self.assertEqual(data['produits_achetes'][0]['produit'], 'produit client')
        self.assertEqual(data['produits_achetes'][0]['total'], '50.00000')

    def test_dashboard_credit_et_paiement_partiel_ne_compte_pas_paiement_comme_achat(self):
        from stock.models import DettesClients

        self._creer_sortie(statut='EN_CREDIT', quantite='1', prix='500')
        dette = DettesClients.objects.get(sortie__client=self.client_fiche)
        pay = self.client.post(
            '/api/paiements-dettes-clients/',
            {'dettes_clients': dette.pk, 'montant': '200'},
            format='json',
        )
        self.assertEqual(pay.status_code, 201, pay.content)

        data = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/').json()
        self.assertEqual(data['nombre_achats'], 1)
        self.assertEqual(data['total_achete'], '500.00000')
        self.assertEqual(data['dette_restante'], '300.00000')
        self.assertEqual(len(data['produits_achetes']), 1)

        # mouvements = produits, pas débit/crédit
        mv = self.client.get(f'/api/clients/{self.client_fiche.pk}/mouvements/?page=1&page_size=25')
        self.assertEqual(mv.status_code, 200)
        results = mv.json()
        if isinstance(results, dict) and 'results' in results:
            results = results['results']
        self.assertEqual(len(results), 1)
        self.assertIn('produit', results[0])
        self.assertNotIn('debit', results[0])
        self.assertNotIn('solde_apres_operation', results[0])

    def test_dashboard_filtre_periode_exclut_achat_hors_periode(self):
        from django.utils import timezone as tz
        from stock.models import DettesClients

        self._creer_sortie(statut='EN_CREDIT', quantite='1', prix='100')
        dette = DettesClients.objects.get(sortie__client=self.client_fiche)
        # dette datée hors période
        dette.date = tz.datetime(2020, 1, 1).date()
        dette.save(update_fields=['date'])
        Sortie.objects.filter(pk=dette.sortie_id).update(
            date_creation=tz.make_aware(tz.datetime(2020, 1, 1, 12, 0, 0))
        )

        data = self.client.get(
            f'/api/clients/{self.client_fiche.pk}/dashboard/'
            f'?date_debut=2026-09-01&date_fin=2026-09-30'
        ).json()
        self.assertEqual(data['nombre_achats'], 0)
        self.assertEqual(data['total_achete'], '0.00000')
        self.assertEqual(data['dette_restante'], '0.00000')
        self.assertEqual(data['produits_achetes'], [])

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class TauxChangeApiTests(APITestCase):
    def setUp(self):
        self.ent = Entreprise.objects.create(
            nom='E-FX',
            secteur='s',
            pays='CD',
            adresse='a',
            telephone='t',
            email='fx@e.com',
            nif='nfx',
            responsable='r',
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


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class EntreeSortieUpdateTests(APITestCase):
    """Tests modification approvisionnements et ventes."""

    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-Update',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='update@example.com',
            nif='n-upd',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_update',
            email='update@example.com',
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
        self.unite = Unite.objects.create(libelle='pc', entreprise=self.entreprise)
        self.type_article = TypeArticle.objects.create(libelle='Divers', entreprise=self.entreprise)
        self.sous_type = SousTypeArticle.objects.create(
            type_article=self.type_article,
            libelle='General',
            entreprise=self.entreprise,
        )
        self.article = Article.objects.create(
            nom_scientifique='produit update',
            nom_commercial='produit update',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='A1',
            entreprise=self.entreprise,
        )
        self.article2 = Article.objects.create(
            nom_scientifique='produit update 2',
            nom_commercial='produit update 2',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='A2',
            entreprise=self.entreprise,
        )
        self.client_fiche = Client.objects.create(id='CLI-UPD', nom='Client Update')
        ClientEntreprise.objects.create(client=self.client_fiche, entreprise=self.entreprise)

    def _create_entree_with_stock(self, quantite='10'):
        entree = Entree.objects.create(libele='Appro test', entreprise=self.entreprise)
        ligne = LigneEntree.objects.create(
            article=self.article,
            entree=entree,
            quantite=Decimal(quantite),
            quantite_restante=Decimal(quantite),
            prix_unitaire=Decimal('2'),
            prix_vente=Decimal('10'),
            devise=self.devise,
            seuil_alerte=Decimal('0'),
        )
        Stock.objects.update_or_create(
            article=self.article,
            defaults={'Qte': Decimal(quantite), 'seuilAlert': Decimal('0')},
        )
        return entree, ligne

    def test_entree_increase_quantity_updates_stock(self):
        entree, ligne = self._create_entree_with_stock('10')
        response = self.client.patch(
            f'/api/entrees/{entree.pk}/',
            {
                'libele': 'Appro test',
                'lignes': [{
                    'id': ligne.pk,
                    'article_id': self.article.pk,
                    'quantite': '15',
                    'prix_unitaire': '2',
                    'prix_vente': '10',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        ligne.refresh_from_db()
        self.assertEqual(ligne.quantite, Decimal('15'))
        self.assertEqual(ligne.quantite_restante, Decimal('15'))
        stock = Stock.objects.get(article=self.article)
        self.assertEqual(stock.Qte, Decimal('15'))

    def test_entree_decrease_quantity_updates_stock(self):
        entree, ligne = self._create_entree_with_stock('10')
        response = self.client.patch(
            f'/api/entrees/{entree.pk}/',
            {
                'libele': 'Appro test',
                'lignes': [{
                    'id': ligne.pk,
                    'article_id': self.article.pk,
                    'quantite': '6',
                    'prix_unitaire': '2',
                    'prix_vente': '10',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        ligne.refresh_from_db()
        self.assertEqual(ligne.quantite, Decimal('6'))
        stock = Stock.objects.get(article=self.article)
        self.assertEqual(stock.Qte, Decimal('6'))

    def test_entree_refuse_decrease_when_partially_sold(self):
        entree, ligne = self._create_entree_with_stock('10')
        ligne.quantite_restante = Decimal('2')
        ligne.save(update_fields=['quantite_restante'])
        response = self.client.patch(
            f'/api/entrees/{entree.pk}/',
            {
                'libele': 'Appro test',
                'lignes': [{
                    'id': ligne.pk,
                    'article_id': self.article.pk,
                    'quantite': '5',
                    'prix_unitaire': '2',
                    'prix_vente': '10',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.content)
        ligne.refresh_from_db()
        self.assertEqual(ligne.quantite, Decimal('10'))

    def test_entree_update_does_not_touch_caisse(self):
        entree, ligne = self._create_entree_with_stock('5')
        count_before = MouvementCaisse.objects.count()
        response = self.client.patch(
            f'/api/entrees/{entree.pk}/',
            {
                'libele': 'Appro modifie',
                'lignes': [{
                    'id': ligne.pk,
                    'article_id': self.article.pk,
                    'quantite': '8',
                    'prix_unitaire': '2',
                    'prix_vente': '10',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(MouvementCaisse.objects.count(), count_before)

    def _create_cash_sortie(self, quantite='3', prix='10'):
        payload = {
            'statut': 'PAYEE',
            'client_id': self.client_fiche.pk,
            'lignes': [{
                'article_id': self.article.pk,
                'quantite': quantite,
                'prix_unitaire': prix,
                'devise_id': self.devise.pk,
            }],
        }
        response = self.client.post('/api/sorties/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return Sortie.objects.get(pk=response.json()['id'])

    def test_sortie_refuse_insufficient_stock(self):
        self._create_entree_with_stock('5')
        sortie = self._create_cash_sortie('2', '10')
        response = self.client.patch(
            f'/api/sorties/{sortie.pk}/',
            {
                'statut': 'PAYEE',
                'client_id': self.client_fiche.pk,
                'lignes': [{
                    'article_id': self.article.pk,
                    'quantite': '20',
                    'prix_unitaire': '10',
                    'devise_id': self.devise.pk,
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_cash_sortie_update_adjusts_single_movement(self):
        self._create_entree_with_stock('100')
        create_resp = self.client.post(
            '/api/sorties/',
            {
                'statut': 'PAYEE',
                'lignes': [{
                    'article_id': self.article.pk,
                    'quantite': '2',
                    'prix_unitaire': '50',
                    'devise_id': self.devise.pk,
                }],
                'type_caisse_id': self.type_caisse.pk,
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.content)
        sortie = Sortie.objects.get(pk=create_resp.json()['id'])
        ref = f'VENT-{sortie.pk}-USD'
        self.assertEqual(MouvementCaisse.objects.filter(sortie=sortie, reference_piece=ref).count(), 1)
        mv = MouvementCaisse.objects.get(sortie=sortie, reference_piece=ref)
        self.assertEqual(mv.montant, Decimal('100.00000'))

        update_resp = self.client.patch(
            f'/api/sorties/{sortie.pk}/',
            {
                'statut': 'PAYEE',
                'lignes': [{
                    'article_id': self.article.pk,
                    'quantite': '1',
                    'prix_unitaire': '50',
                    'devise_id': self.devise.pk,
                }],
                'type_caisse_id': self.type_caisse.pk,
            },
            format='json',
        )
        self.assertEqual(update_resp.status_code, 200, update_resp.content)
        self.assertEqual(MouvementCaisse.objects.filter(sortie=sortie, reference_piece=ref).count(), 1)
        mv.refresh_from_db()
        self.assertEqual(mv.montant, Decimal('50.00000'))
        self.assertFalse(MouvementCaisse.objects.filter(reference_piece__startswith='AJ-VENT-').exists())

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class ConditionnementPricingTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-cond',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='cond@e.com',
            nif='n-cond',
            responsable='r-cond',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_cond',
            email='cond@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user,
            entreprise=self.entreprise,
            role='admin',
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

        self.unite = Unite.objects.create(libelle='Bouteille', entreprise=self.entreprise)
        self.type_article = TypeArticle.objects.create(libelle='Boisson', entreprise=self.entreprise)
        self.sous_type = SousTypeArticle.objects.create(
            type_article=self.type_article,
            libelle='Eau',
            entreprise=self.entreprise,
        )
        self.devise = Devise.objects.create(
            sigle='USD',
            nom='Dollar',
            symbole='$',
            est_principal=True,
            entreprise=self.entreprise,
        )
        self.article = Article.objects.create(
            nom_scientifique='Eau 500ml',
            nom_commercial='Eau',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='A1',
            entreprise=self.entreprise,
        )
        self.cond_piece = ConditionnementArticle.objects.create(
            article=self.article,
            nom='Bouteille',
            multiplicateur_base=Decimal('1'),
            est_defaut=True,
        )
        self.cond_carton = ConditionnementArticle.objects.create(
            article=self.article,
            nom='Carton 24',
            multiplicateur_base=Decimal('24'),
            est_defaut=False,
        )

    def test_create_entree_with_conditionnement_converts_to_base(self):
        payload = {
            'libele': 'Appro eau carton',
            'description': 'test conversion conditionnement',
            'lignes': [
                {
                    'article_id': self.article.pk,
                    'conditionnement_id': self.cond_carton.pk,
                    'quantite_saisie': '10',
                    'prix_achat_conditionnement': '12',
                    'prix_vente_conditionnement': '15',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                }
            ],
        }
        response = self.client.post('/api/entrees/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        ligne = LigneEntree.objects.get(article=self.article)
        self.assertEqual(ligne.quantite, Decimal('240.00000'))
        self.assertEqual(ligne.quantite_restante, Decimal('240.00000'))
        self.assertEqual(ligne.prix_unitaire, Decimal('0.50000'))
        self.assertEqual(ligne.prix_vente, Decimal('0.62500'))
        self.assertEqual(ligne.conditionnement_id, self.cond_carton.id)
        self.assertEqual(ligne.quantite_saisie, Decimal('10.00000'))

    def test_conditionnement_and_prix_conditionnement_endpoints(self):
        create_cond_resp = self.client.post(
            '/api/conditionnements-articles/',
            {
                'article_id': self.article.pk,
                'nom': 'Pack 12',
                'multiplicateur_base': '12',
                'est_defaut': False,
            },
            format='json',
        )
        self.assertEqual(create_cond_resp.status_code, 201, create_cond_resp.content)
        cond_pack_id = create_cond_resp.json()['id']

        entree_resp = self.client.post(
            '/api/entrees/',
            {
                'libele': 'Appro lot endpoint',
                'description': 'test endpoint prix conditionnement',
                'lignes': [
                    {
                        'article_id': self.article.pk,
                        'quantite': '24',
                        'prix_unitaire': '0.5',
                        'prix_vente': '0.75',
                        'devise_id': self.devise.pk,
                        'seuil_alerte': '0',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(entree_resp.status_code, 201, entree_resp.content)
        ligne_entree = LigneEntree.objects.get(article=self.article, entree_id=entree_resp.json()['id'])

        prix_resp = self.client.post(
            '/api/prix-conditionnement-entrees/',
            {
                'ligne_entree_id': ligne_entree.id,
                'conditionnement_id': cond_pack_id,
                'prix_vente': '8',
                'devise_id': self.devise.pk,
                'est_prix_principal': True,
            },
            format='json',
        )
        self.assertEqual(prix_resp.status_code, 201, prix_resp.content)
        self.assertEqual(
            PrixConditionnementEntree.objects.filter(ligne_entree=ligne_entree, conditionnement_id=cond_pack_id).count(),
            1,
        )

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class CodeBarresArticleTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-barcode',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='barcode@e.com',
            nif='n-barcode',
            responsable='r-barcode',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_barcode',
            email='barcode@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user,
            entreprise=self.entreprise,
            role='admin',
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

        self.unite = Unite.objects.create(libelle='Pc', entreprise=self.entreprise)
        self.type_article = TypeArticle.objects.create(libelle='Matiere', entreprise=self.entreprise)
        self.sous_type = SousTypeArticle.objects.create(
            type_article=self.type_article,
            libelle='Plastique',
            entreprise=self.entreprise,
        )
        self.devise = Devise.objects.create(
            sigle='USD',
            nom='Dollar',
            symbole='$',
            est_principal=True,
            entreprise=self.entreprise,
        )
        self.article = Article.objects.create(
            nom_scientifique='Plastique',
            nom_commercial='plastique',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='A1',
            entreprise=self.entreprise,
        )
        self.cond_piece = ConditionnementArticle.objects.create(
            article=self.article,
            nom='Pc',
            multiplicateur_base=Decimal('1'),
            est_defaut=True,
        )
        self.cond_plaque = ConditionnementArticle.objects.create(
            article=self.article,
            nom='Plaque',
            multiplicateur_base=Decimal('16'),
            est_defaut=False,
        )
        Stock.objects.create(article=self.article, Qte=0, seuilAlert=0)

    def _create_entree_stock(self):
        payload = {
            'libele': 'Appro plastique',
            'description': 'stock barcode test',
            'lignes': [
                {
                    'article_id': self.article.pk,
                    'conditionnement_id': self.cond_plaque.pk,
                    'quantite_saisie': '2',
                    'prix_achat_conditionnement': '18',
                    'prix_vente_conditionnement': '21',
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                }
            ],
        }
        response = self.client.post('/api/entrees/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.content)

    def test_create_code_barres_on_conditionnement(self):
        response = self.client.post(
            '/api/codes-barres-articles/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_plaque.pk,
                'code': '123456789016',
                'type_code': 'EAN13',
                'est_principal': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data['code'], '123456789016')
        self.assertEqual(data['conditionnement']['nom'], 'Plaque')

    def test_duplicate_code_rejected(self):
        self.client.post(
            '/api/codes-barres-articles/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_plaque.pk,
                'code': '9999999999999',
            },
            format='json',
        )
        other_article = Article.objects.create(
            nom_scientifique='Autre article',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='B1',
            entreprise=self.entreprise,
        )
        other_cond = ConditionnementArticle.objects.create(
            article=other_article,
            nom='Unité',
            multiplicateur_base=Decimal('1'),
            est_defaut=True,
        )
        response = self.client.post(
            '/api/codes-barres-articles/',
            {
                'article_id': other_article.pk,
                'conditionnement_id': other_cond.pk,
                'code': '9999999999999',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('code', response.json())

    def test_lookup_found_with_price_and_stock(self):
        self._create_entree_stock()
        self.client.post(
            '/api/codes-barres-articles/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_plaque.pk,
                'code': '123456789016',
            },
            format='json',
        )
        response = self.client.get('/api/stock/code-barres/lookup/?code=123456789016')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data['found'])
        self.assertEqual(data['article']['id'], self.article.pk)
        self.assertEqual(data['conditionnement']['nom'], 'Plaque')
        self.assertEqual(data['conditionnement']['quantite_base'], '16.00000')
        self.assertEqual(data['stock']['quantite_base'], '32.00000')
        self.assertEqual(data['prix']['montant'], '21.00000')
        self.assertEqual(data['prix']['devise'], 'USD')
        self.assertIn(data['prix']['source'], (
            'prix_conditionnement_ligne',
            'prix_conditionnement_fifo',
            'prix_unitaire_base_fifo',
        ))

    def test_lookup_not_found(self):
        response = self.client.get('/api/stock/code-barres/lookup/?code=0000000000000')
        self.assertEqual(response.status_code, 404, response.content)
        data = response.json()
        self.assertFalse(data['found'])
        self.assertIn('message', data)

    def test_lookup_inactive_code_not_found(self):
        create_resp = self.client.post(
            '/api/codes-barres-articles/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_piece.pk,
                'code': '1111111111111',
            },
            format='json',
        )
        cb_id = create_resp.json()['id']
        patch_resp = self.client.patch(
            f'/api/codes-barres-articles/{cb_id}/',
            {'est_actif': False},
            format='json',
        )
        self.assertEqual(patch_resp.status_code, 200, patch_resp.content)
        lookup_resp = self.client.get('/api/stock/code-barres/lookup/?code=1111111111111')
        self.assertEqual(lookup_resp.status_code, 404, lookup_resp.content)

    def test_generer_code_interne_numerique(self):
        response = self.client.post(
            '/api/codes-barres-articles/generer/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_plaque.pk,
                'format': 'numerique',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertTrue(data['code'].startswith('20'))
        self.assertEqual(data['type_code'], 'CODE128')
        self.assertIn('etiquette_url', data)

    def test_generer_refuse_si_code_existe(self):
        self.client.post(
            '/api/codes-barres-articles/generer/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_piece.pk,
            },
            format='json',
        )
        response = self.client.post(
            '/api/codes-barres-articles/generer/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_piece.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_generer_manquants(self):
        response = self.client.post(
            '/api/codes-barres-articles/generer-manquants/',
            {'article_id': self.article.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['count'], 2)

    def test_etiquette_pdf(self):
        gen = self.client.post(
            '/api/codes-barres-articles/generer/',
            {
                'article_id': self.article.pk,
                'conditionnement_id': self.cond_plaque.pk,
            },
            format='json',
        )
        cb_id = gen.json()['id']
        response = self.client.get(f'/api/codes-barres-articles/{cb_id}/etiquette/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class DettesClientsApiTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-Dettes',
            secteur='s',
            pays='CD',
            adresse='a',
            telephone='t',
            email='dettes@example.com',
            nif='n-dettes',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_dettes',
            email='admin-dettes@example.com',
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
        self.unite = Unite.objects.create(libelle='pc', entreprise=self.entreprise)
        self.type_article = TypeArticle.objects.create(libelle='Divers', entreprise=self.entreprise)
        self.sous_type = SousTypeArticle.objects.create(
            type_article=self.type_article,
            libelle='General',
            entreprise=self.entreprise,
        )
        self.article = Article.objects.create(
            nom_scientifique='article dette',
            nom_commercial='article dette',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='A1',
            entreprise=self.entreprise,
        )
        Stock.objects.create(article=self.article, Qte=Decimal('100'), seuilAlert=Decimal('0'))
        entree = Entree.objects.create(libele='Appro dettes', entreprise=self.entreprise)
        LigneEntree.objects.create(
            article=self.article,
            entree=entree,
            quantite=Decimal('100'),
            quantite_restante=Decimal('100'),
            prix_unitaire=Decimal('5'),
            prix_vente=Decimal('500'),
            devise=self.devise,
            seuil_alerte=Decimal('0'),
        )
        self.client_fiche = Client.objects.create(id='CLI-DETTE', nom='Client Dette')
        ClientEntreprise.objects.create(client=self.client_fiche, entreprise=self.entreprise)

    def _creer_sortie_credit(self, quantite='1', prix='500'):
        response = self.client.post(
            '/api/sorties/',
            {
                'statut': 'EN_CREDIT',
                'client_id': self.client_fiche.pk,
                'lignes': [{
                    'article_id': self.article.pk,
                    'quantite': quantite,
                    'prix_unitaire': prix,
                    'devise_id': self.devise.pk,
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_paiement_partiel_puis_solde(self):
        from stock.models import DettesClients, PaiementDettesClients

        self._creer_sortie_credit()
        dette = DettesClients.objects.get(sortie__client=self.client_fiche)
        self.assertEqual(dette.reste, Decimal('500.00000'))

        r1 = self.client.post(
            '/api/paiements-dettes-clients/',
            {'dettes_clients': dette.pk, 'montant': '100', 'date': '2026-09-01'},
            format='json',
        )
        self.assertEqual(r1.status_code, 201, r1.content)
        dette.refresh_from_db()
        self.assertEqual(dette.paye, Decimal('100.00000'))
        self.assertEqual(dette.reste, Decimal('400.00000'))
        self.assertEqual(dette.status, DettesClients.STATUS_ENCOURS)

        r2 = self.client.post(
            '/api/paiements-dettes-clients/',
            {'dettes_clients': dette.pk, 'montant': '400', 'date': '2026-09-10'},
            format='json',
        )
        self.assertEqual(r2.status_code, 201, r2.content)
        dette.refresh_from_db()
        self.assertEqual(dette.reste, Decimal('0.00000'))
        self.assertEqual(dette.status, DettesClients.STATUS_TERMINE)
        self.assertEqual(PaiementDettesClients.objects.filter(dettes_clients=dette).count(), 2)

        r3 = self.client.post(
            '/api/paiements-dettes-clients/',
            {'dettes_clients': dette.pk, 'montant': '1'},
            format='json',
        )
        self.assertEqual(r3.status_code, 400, r3.content)

    def test_par_clients_et_totaux(self):
        self._creer_sortie_credit(prix='100')
        self._creer_sortie_credit(prix='250')
        response = self.client.get('/api/dettes-clients/par-clients/')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['total_reste'], '350.00000')
        self.assertEqual(len(data['clients']), 1)
        self.assertEqual(data['clients'][0]['total_reste'], '350.00000')

        detail = self.client.get('/api/dettes-clients/')
        self.assertEqual(detail.status_code, 200)
        results = detail.json()
        if isinstance(results, dict) and 'results' in results:
            results = results['results']
        self.assertEqual(len(results), 2)
        # Liste légère : pas d'articles embarqués
        self.assertNotIn('articles', results[0])

        fiche = self.client.get(f"/api/dettes-clients/{results[0]['id']}/")
        self.assertEqual(fiche.status_code, 200)
        self.assertIn('articles', fiche.json())
        self.assertIn('paiements', fiche.json())
