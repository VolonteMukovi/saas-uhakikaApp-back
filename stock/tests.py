"""
Tests isolation multi-tenant (endpoints m├⌐tier).
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from caisse.models import MouvementCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse
from stock.models import (
    Article,
    ConditionnementArticle,
    Client,
    ClientEntreprise,
    Devise,
    DetteClient,
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
    """Vente EN_CREDIT ΓåÆ dette obligatoire ; coh├⌐rence dashboard."""

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

    def test_dashboard_credit_stats_reset_after_dette_deletion(self):
        """Après suppression des dettes, total_credit / CA crédit ne restent pas fantômes."""
        r1 = self.client.post(
            '/api/sorties/', self._credit_sortie_payload(montant='20.00000'), format='json',
        )
        self.assertEqual(r1.status_code, 201, r1.content)
        r2 = self.client.post(
            '/api/sorties/', self._credit_sortie_payload(montant='15.00000'), format='json',
        )
        self.assertEqual(r2.status_code, 201, r2.content)

        dash = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/')
        resume = dash.json()['resume']
        self.assertEqual(resume['nombre_dettes'], 2)
        self.assertEqual(resume['total_credit'], '105.00000')  # 3*20 + 3*15
        self.assertEqual(resume['total_dettes'], '105.00000')
        self.assertEqual(resume['chiffre_affaires_total'], '105.00000')

        dette_a = DetteClient.objects.get(sortie_id=r1.json()['id'])
        del_a = self.client.delete(
            f'/api/dettes/{dette_a.pk}/',
            {'confirm': True, 'reason': 'Suppression dette A'},
            format='json',
        )
        self.assertEqual(del_a.status_code, 200, del_a.content)

        dash2 = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/')
        resume2 = dash2.json()['resume']
        self.assertEqual(resume2['nombre_dettes'], 1)
        self.assertEqual(resume2['total_credit'], '45.00000')
        self.assertEqual(resume2['total_dettes'], '45.00000')
        self.assertEqual(resume2['solde_restant'], '45.00000')
        self.assertEqual(resume2['chiffre_affaires_total'], '45.00000')
        self.assertEqual(dash2.json()['repartition']['credit'], '45.00000')

        cleanup = self.client.post(
            '/api/dettes/cleanup-client/',
            {
                'client_id': self.client_fiche.pk,
                'confirm': True,
                'reason': 'Nettoyage final',
            },
            format='json',
        )
        self.assertEqual(cleanup.status_code, 200, cleanup.content)

        dash3 = self.client.get(f'/api/clients/{self.client_fiche.pk}/dashboard/')
        resume3 = dash3.json()['resume']
        self.assertEqual(resume3['nombre_dettes'], 0)
        self.assertEqual(resume3['total_credit'], '0.00000')
        self.assertEqual(resume3['total_dettes'], '0.00000')
        self.assertEqual(resume3['solde_restant'], '0.00000')
        self.assertEqual(resume3['chiffre_affaires_total'], '0.00000')
        self.assertEqual(resume3['nombre_ventes'], 0)
        self.assertEqual(resume3['nombre_paiements'], 0)
        self.assertEqual(resume3['nombre_operations'], 0)
        self.assertEqual(dash3.json()['repartition']['credit'], '0.00000')

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

    def _create_credit_sortie(self, quantite='3', prix='10'):
        payload = {
            'statut': 'EN_CREDIT',
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

    def test_credit_sortie_update_adjusts_dette(self):
        self._create_entree_with_stock('100')
        sortie = self._create_credit_sortie('3', '10')
        dette = DetteClient.objects.get(sortie=sortie)
        self.assertEqual(dette.montant_total, Decimal('30.00000'))

        response = self.client.patch(
            f'/api/sorties/{sortie.pk}/',
            {
                'statut': 'EN_CREDIT',
                'client_id': self.client_fiche.pk,
                'lignes': [{
                    'article_id': self.article.pk,
                    'quantite': '2',
                    'prix_unitaire': '10',
                    'devise_id': self.devise.pk,
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        dette.refresh_from_db()
        self.assertEqual(dette.montant_total, Decimal('20.00000'))

    def test_credit_sortie_refuse_total_below_paid(self):
        self._create_entree_with_stock('100')
        sortie = self._create_credit_sortie('10', '10')
        dette = DetteClient.objects.get(sortie=sortie)
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        MouvementCaisse.objects.create(
            montant=Decimal('70.00000'),
            devise=self.devise,
            type='ENTREE',
            motif='Paiement partiel',
            content_type=ct_dette,
            object_id=dette.pk,
            utilisateur=self.user,
            reference_piece='PAY-UPD-1',
            entreprise=self.entreprise,
            type_caisse=self.type_caisse,
            categorie='PAIEMENT_DETTE',
        )
        response = self.client.patch(
            f'/api/sorties/{sortie.pk}/',
            {
                'statut': 'EN_CREDIT',
                'client_id': self.client_fiche.pk,
                'lignes': [{
                    'article_id': self.article.pk,
                    'quantite': '5',
                    'prix_unitaire': '10',
                    'devise_id': self.devise.pk,
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.content)
        dette.refresh_from_db()
        self.assertEqual(dette.montant_total, Decimal('100.00000'))

    def test_sortie_refuse_insufficient_stock(self):
        self._create_entree_with_stock('5')
        sortie = self._create_credit_sortie('2', '10')
        response = self.client.patch(
            f'/api/sorties/{sortie.pk}/',
            {
                'statut': 'EN_CREDIT',
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

