"""
Tests isolation multi-tenant (endpoints métier).
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from caisse.models import MouvementCaisse, TypeCaisse
from stock.models import (
    Article,
    Client,
    ClientEntreprise,
    Devise,
    DetteClient,
    Entreprise,
    Entree,
    LigneEntree,
    LigneSortie,
    Sortie,
    Stock,
    SousTypeArticle,
    TypeArticle,
    Unite,
)
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

    def test_client_dashboard_and_movements_include_sales_and_payments(self):
        sortie_cash = Sortie.objects.create(
            client=self.client_fiche,
            devise=self.devise,
            statut='PAYEE',
            entreprise=self.entreprise,
        )
        self._add_line(sortie_cash, '2', '5')

        sortie_credit = Sortie.objects.create(
            client=self.client_fiche,
            devise=self.devise,
            statut='EN_CREDIT',
            entreprise=self.entreprise,
        )
        self._add_line(sortie_credit, '3', '4')

        dette = DetteClient.objects.create(
            client=self.client_fiche,
            sortie=sortie_credit,
            montant_total=Decimal('12.00000'),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal('12.00000'),
            entreprise=self.entreprise,
            statut='EN_COURS',
        )
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        MouvementCaisse.objects.create(
            montant=Decimal('7.00000'),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal('7.00000'),
            type='ENTREE',
            motif='Paiement partiel',
            moyen='Banque',
            content_type=ct_dette,
            object_id=dette.pk,
            utilisateur=self.user,
            reference_piece='PAY-CL-1',
            entreprise=self.entreprise,
            type_caisse=self.type_caisse,
            categorie='PAIEMENT_DETTE',
        )

        response = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/')
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload['resume']['chiffre_affaires_total'], '22.00000')
        self.assertEqual(payload['resume']['total_comptant'], '10.00000')
        self.assertEqual(payload['resume']['total_credit'], '12.00000')
        self.assertEqual(payload['resume']['total_paye'], '7.00000')
        self.assertEqual(payload['resume']['solde_restant'], '5.00000')
        self.assertEqual(payload['resume']['nombre_ventes'], 2)
        self.assertEqual(payload['resume']['nombre_dettes'], 1)
        self.assertEqual(payload['resume']['nombre_paiements'], 1)
        self.assertEqual(payload['totaux_par_devise'][0]['solde'], '5.00000')

        movements_response = self.client.get(f'/api/clients/{self.client_fiche.pk}/mouvements/')
        self.assertEqual(movements_response.status_code, 200, movements_response.content)
        movements = movements_response.json()['results']
        self.assertEqual([item['type'] for item in movements], ['PAIEMENT_DETTE', 'VENTE_CREDIT', 'VENTE_COMPTANT'])
        self.assertEqual(movements[0]['solde_apres_operation'], '5.00000')
        self.assertEqual(movements[1]['solde_apres_operation'], '12.00000')
        self.assertEqual(movements[2]['solde_apres_operation'], '0.00000')

    def test_client_dashboard_respects_period_filters(self):
        old_sortie = Sortie.objects.create(
            client=self.client_fiche,
            devise=self.devise,
            statut='PAYEE',
            entreprise=self.entreprise,
        )
        self._add_line(old_sortie, '1', '9')

        recent_sortie = Sortie.objects.create(
            client=self.client_fiche,
            devise=self.devise,
            statut='EN_CREDIT',
            entreprise=self.entreprise,
        )
        self._add_line(recent_sortie, '2', '6')
        dette = DetteClient.objects.create(
            client=self.client_fiche,
            sortie=recent_sortie,
            montant_total=Decimal('12.00000'),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal('12.00000'),
            entreprise=self.entreprise,
            statut='EN_COURS',
        )
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        paiement = MouvementCaisse.objects.create(
            montant=Decimal('4.00000'),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal('4.00000'),
            type='ENTREE',
            motif='Paiement recent',
            moyen='Banque',
            content_type=ct_dette,
            object_id=dette.pk,
            utilisateur=self.user,
            reference_piece='PAY-RECENT',
            entreprise=self.entreprise,
            type_caisse=self.type_caisse,
            categorie='PAIEMENT_DETTE',
        )

        old_date = timezone.now() - timezone.timedelta(days=10)
        recent_date = timezone.now() - timezone.timedelta(days=1)
        Sortie.objects.filter(pk=old_sortie.pk).update(date_creation=old_date)
        Sortie.objects.filter(pk=recent_sortie.pk).update(date_creation=recent_date)
        DetteClient.objects.filter(pk=dette.pk).update(date_creation=recent_date)
        MouvementCaisse.objects.filter(pk=paiement.pk).update(date=recent_date)

        response = self.client.get(
            f'/api/clients/{self.client_fiche.pk}/dashboard/',
            {'date_debut': recent_date.date().isoformat(), 'date_fin': recent_date.date().isoformat()},
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload['resume']['chiffre_affaires_total'], '12.00000')
        self.assertEqual(payload['resume']['total_comptant'], '0.00000')
        self.assertEqual(payload['resume']['total_credit'], '12.00000')
        self.assertEqual(payload['resume']['total_paye'], '4.00000')
        self.assertEqual(payload['resume']['solde_restant'], '8.00000')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class CreditSaleDebtTests(APITestCase):
    """Vente EN_CREDIT → dette obligatoire ; cohérence dashboard."""

    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-Credit',
            secteur='s',
            pays='FR',
            adresse='a',
            telephone='t',
            email='credit@example.com',
            nif='n-credit',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_credit',
            email='admin-credit@example.com',
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
            nom_scientifique='produit credit',
            nom_commercial='produit credit',
            sous_type_article=self.sous_type,
            unite=self.unite,
            emplacement='A1',
            entreprise=self.entreprise,
        )
        entree = Entree.objects.create(
            libele='Stock test credit',
            entreprise=self.entreprise,
        )
        LigneEntree.objects.create(
            article=self.article,
            entree=entree,
            quantite=Decimal('100'),
            quantite_restante=Decimal('100'),
            prix_unitaire=Decimal('1'),
            prix_vente=Decimal('10'),
            devise=self.devise,
            seuil_alerte=Decimal('0'),
        )
        Stock.objects.create(article=self.article, Qte=Decimal('100'), seuilAlert=Decimal('0'))
        self.client_fiche = Client.objects.create(id='CLI-CRED', nom='Client Credit')
        ClientEntreprise.objects.create(client=self.client_fiche, entreprise=self.entreprise)

    def _credit_sortie_payload(self, *, montant='30.00000', client_id=None):
        return {
            'statut': 'EN_CREDIT',
            'client_id': client_id or self.client_fiche.pk,
            'lignes': [
                {
                    'article_id': self.article.pk,
                    'quantite': '3',
                    'prix_unitaire': montant,
                    'devise_id': self.devise.pk,
                }
            ],
        }

    def test_credit_sortie_creates_dette_atomically(self):
        response = self.client.post('/api/sorties/', self._credit_sortie_payload(), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        sortie_id = response.json()['id']
        sortie = Sortie.objects.get(pk=sortie_id)
        self.assertEqual(sortie.statut, 'EN_CREDIT')
        self.assertEqual(sortie.devise_id, self.devise.pk)
        dette = DetteClient.objects.get(sortie=sortie)
        self.assertEqual(dette.client_id, self.client_fiche.pk)
        self.assertEqual(dette.montant_total, Decimal('90.00000'))
        self.assertEqual(dette.statut, 'EN_COURS')

    def test_credit_sortie_without_client_rejected(self):
        payload = self._credit_sortie_payload()
        payload.pop('client_id')
        response = self.client.post('/api/sorties/', payload, format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Sortie.objects.filter(statut='EN_CREDIT').exists())

    def test_dashboard_totals_align_after_credit_sale(self):
        self.client.post('/api/sorties/', self._credit_sortie_payload(montant='10.00000'), format='json')
        dash = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/')
        self.assertEqual(dash.status_code, 200, dash.content)
        resume = dash.json()['resume']
        self.assertEqual(resume['total_credit'], '30.00000')
        self.assertEqual(resume['total_dettes'], '30.00000')
        self.assertEqual(resume['solde_restant'], '30.00000')
        self.assertEqual(resume['nombre_dettes'], 1)

    def test_repair_command_creates_missing_debt(self):
        sortie = Sortie.objects.create(
            client=self.client_fiche,
            statut='EN_CREDIT',
            entreprise=self.entreprise,
        )
        LigneSortie.objects.create(
            sortie=sortie,
            article=self.article,
            quantite=Decimal('2'),
            prix_unitaire=Decimal('15'),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal('30'),
        )
        self.assertFalse(DetteClient.objects.filter(sortie=sortie).exists())
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('repair_credit_sale_debts', '--entreprise-id', str(self.entreprise.pk), stdout=out)
        dette = DetteClient.objects.get(sortie=sortie)
        self.assertEqual(dette.montant_total, Decimal('30.00000'))

    def test_totaux_par_devise_matches_resume_payments(self):
        sortie = Sortie.objects.create(
            client=self.client_fiche,
            devise=self.devise,
            statut='EN_CREDIT',
            entreprise=self.entreprise,
        )
        LigneSortie.objects.create(
            sortie=sortie,
            article=self.article,
            quantite=Decimal('1'),
            prix_unitaire=Decimal('47.93'),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal('47.93'),
        )
        dette = DetteClient.objects.create(
            client=self.client_fiche,
            sortie=sortie,
            montant_total=Decimal('47.93000'),
            devise=self.devise,
            devise_reference=self.devise,
            montant_reference=Decimal('47.93'),
            entreprise=self.entreprise,
            statut='EN_COURS',
        )
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        for amount, ref in [('4.50000', 'P1'), ('43.43000', 'P2')]:
            MouvementCaisse.objects.create(
                montant=Decimal(amount),
                devise=None,
                type='ENTREE',
                motif='Paiement',
                content_type=ct_dette,
                object_id=dette.pk,
                utilisateur=self.user,
                reference_piece=ref,
                entreprise=self.entreprise,
                categorie='PAIEMENT_DETTE',
            )
        dash = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/')
        payload = dash.json()
        self.assertEqual(payload['resume']['total_paye'], '47.93000')
        self.assertEqual(payload['totaux_par_devise'][0]['total_paye'], '47.93000')
        self.assertEqual(payload['totaux_par_devise'][0]['solde'], '0.00000')

    def test_delete_specific_dette_also_deletes_related_payments(self):
        response = self.client.post('/api/sorties/', self._credit_sortie_payload(montant='10.00000'), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        sortie = Sortie.objects.get(pk=response.json()['id'])
        dette = DetteClient.objects.get(sortie=sortie)
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        paiement = MouvementCaisse.objects.create(
            montant=Decimal('5.00000'),
            devise=self.devise,
            type='ENTREE',
            motif='Paiement test suppression',
            content_type=ct_dette,
            object_id=dette.pk,
            utilisateur=self.user,
            reference_piece='PAY-DEL-1',
            entreprise=self.entreprise,
            categorie='PAIEMENT_DETTE',
        )
        delete_resp = self.client.delete(
            f'/api/dettes/{dette.pk}/',
            {'confirm': True, 'reason': 'Correction ancienne dette'},
            format='json',
        )
        self.assertEqual(delete_resp.status_code, 200, delete_resp.content)
        self.assertFalse(DetteClient.objects.filter(pk=dette.pk).exists())
        self.assertFalse(MouvementCaisse.objects.filter(pk=paiement.pk).exists())

    def test_cleanup_client_deletes_all_dettes_and_related_payments(self):
        for idx, montant in enumerate(['10.00000', '15.00000'], start=1):
            response = self.client.post('/api/sorties/', self._credit_sortie_payload(montant=montant), format='json')
            self.assertEqual(response.status_code, 201, response.content)
            sortie = Sortie.objects.get(pk=response.json()['id'])
            dette = DetteClient.objects.get(sortie=sortie)
            ct_dette = ContentType.objects.get_for_model(DetteClient)
            MouvementCaisse.objects.create(
                montant=Decimal('1.00000'),
                devise=self.devise,
                type='ENTREE',
                motif='Paiement test nettoyage',
                content_type=ct_dette,
                object_id=dette.pk,
                utilisateur=self.user,
                reference_piece=f'PAY-CLEAN-{idx}',
                entreprise=self.entreprise,
                categorie='PAIEMENT_DETTE',
            )

        cleanup_resp = self.client.post(
            '/api/dettes/cleanup-client/',
            {
                'client_id': self.client_fiche.pk,
                'confirm': True,
                'reason': 'Nettoyage dettes incoherentes',
            },
            format='json',
        )
        self.assertEqual(cleanup_resp.status_code, 200, cleanup_resp.content)
        self.assertEqual(
            DetteClient.objects.filter(client=self.client_fiche, entreprise=self.entreprise).count(),
            0,
        )
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        self.assertEqual(
            MouvementCaisse.objects.filter(content_type=ct_dette, categorie='PAIEMENT_DETTE').count(),
            0,
        )

    def test_manual_create_dette_does_not_touch_stock_and_sets_partial_paid(self):
        stock_before = Stock.objects.get(article=self.article).Qte
        resp = self.client.post(
            '/api/dettes/manual-create/',
            {
                'client_id': self.client_fiche.pk,
                'montant_total': '100.00000',
                'montant_deja_paye': '40.00000',
                'devise_id': self.devise.pk,
                'commentaire': 'Reprise cahier physique',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        dette_id = resp.json()['dette']['id']
        dette = DetteClient.objects.get(pk=dette_id)
        self.assertEqual(dette.montant_total, Decimal('100.00000'))
        self.assertEqual(dette.montant_paye, Decimal('40.00000'))
        self.assertEqual(dette.solde_restant, Decimal('60.00000'))
        self.assertEqual(dette.statut, 'EN_COURS')
        self.assertEqual(dette.sortie.lignes.count(), 0)
        stock_after = Stock.objects.get(article=self.article).Qte
        self.assertEqual(stock_before, stock_after)

