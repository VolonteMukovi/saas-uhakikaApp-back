"""
Sorties non commerciales sans impact caisse, et annulation des entrées / sorties de stock.
"""
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from caisse.models import MouvementCaisse, SessionCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse
from caisse.services.caisse_defaut import CaisseError
from caisse.services.session_caisse import solde_session_courant
from stock.models import (
    AnnulationMouvement,
    Article,
    BeneficeLot,
    Client,
    ClientEntreprise,
    DettesClients,
    Devise,
    Entree,
    Entreprise,
    LigneEntree,
    LigneSortieLot,
    Requisition,
    RequisitionHistorique,
    Sortie,
    SousTypeArticle,
    Stock,
    TypeArticle,
    Unite,
)
from stock.services.sortie_motif import est_sortie_commerciale
from users.models import Membership

D = Decimal


class SortieMotifTests(SimpleTestCase):
    def test_motifs_commerciaux(self):
        for motif in ('Vente au Client', 'vente au client', '', None, 'Vente du jour', 'Vente à crédit', 'Import Excel'):
            with self.subTest(motif=motif):
                self.assertTrue(est_sortie_commerciale(motif))

    def test_motifs_non_commerciaux(self):
        for motif in (
            'Produit défectueux', 'Matériel défectueux', 'Produit périmé', 'Produit volé', 'Perte/Vol',
            'Produit endommagé', 'Perte ou destruction', 'Échantillon/Démonstration', 'Prêt/Formation',
            'Cadeau client', 'Casse en entrepôt',
        ):
            with self.subTest(motif=motif):
                self.assertFalse(est_sortie_commerciale(motif))


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class MouvementStockBase(APITestCase):
    def setUp(self):
        self.entreprise = self._entreprise('E-Annul', 'annul@example.com')
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin_annul', email='admin-annul@example.com', password='x-secret-123')
        Membership.objects.create(user=self.admin, entreprise=self.entreprise, role='admin', is_active=True)
        self.agent = User.objects.create_user(username='agent_annul', email='agent-annul@example.com', password='x-secret-123')
        Membership.objects.create(user=self.agent, entreprise=self.entreprise, role='user', is_active=True)
        self.client.force_authenticate(user=self.admin)

        self.devise = Devise.objects.create(sigle='USD', nom='Dollar', symbole='$', est_principal=True, entreprise=self.entreprise)
        self.caisse = TypeCaisse.objects.create(
            nom='Caisse principale', libelle='Caisse principale', code_type='CASH', devise=self.devise,
            entreprise=self.entreprise, is_active=True, est_defaut=True,
        )
        self.session = SessionCaisse.objects.create(
            numero='TEST-ANNUL-SESSION', type_caisse=self.caisse, devise=self.devise, entreprise=self.entreprise,
            ouvert_le=timezone.now(), solde_ouverture=D('500'), statut='OUVERTE',
        )
        unite = Unite.objects.create(libelle='pc', entreprise=self.entreprise)
        type_article = TypeArticle.objects.create(libelle='Divers', entreprise=self.entreprise)
        sous_type = SousTypeArticle.objects.create(type_article=type_article, libelle='General', entreprise=self.entreprise)
        self.article = Article.objects.create(
            nom_scientifique='article annul', nom_commercial='article annul', sous_type_article=sous_type,
            unite=unite, emplacement='A1', entreprise=self.entreprise,
        )
        self.client_fiche = Client.objects.create(id='CLI-ANNUL', nom='Client Annul')
        ClientEntreprise.objects.create(client=self.client_fiche, entreprise=self.entreprise)

    @staticmethod
    def _entreprise(nom, email):
        return Entreprise.objects.create(
            nom=nom, secteur='s', pays='CD', adresse='a', telephone='t', email=email, nif=f'nif-{nom}', responsable='r',
        )

    # -- helpers -----------------------------------------------------------
    def solde(self):
        return solde_session_courant(self.session)

    def stock(self):
        return Stock.objects.get(article=self.article).Qte

    def approvisionner(self, quantite, prix_achat='2', prix_vente='10'):
        response = self.client.post(
            '/api/entrees/',
            {
                'libele': 'Appro test',
                'lignes': [{
                    'article_id': self.article.pk,
                    'quantite': str(quantite),
                    'prix_unitaire': prix_achat,
                    'prix_vente': prix_vente,
                    'devise_id': self.devise.pk,
                    'seuil_alerte': '0',
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        return Entree.objects.get(pk=response.json()['id'])

    def payer_appro(self, entree, montant):
        return creer_mouvement_caisse(
            montant=D(montant), devise=self.devise, type_mouvement='SORTIE', entreprise_id=self.entreprise.pk,
            succursale_id=None, entree=entree, content_object=entree, reference_piece=f'APPRO-{entree.pk}',
            utilisateur=self.admin, type_caisse=self.caisse, categorie='APPROVISIONNEMENT',
        )

    def sortir(self, quantite, prix='10', *, motif='Vente au Client', statut='PAYEE', caisse=True, expect=201):
        payload = {
            'motif': motif,
            'statut': statut,
            'client_id': self.client_fiche.pk,
            'lignes': [{
                'article_id': self.article.pk,
                'quantite': str(quantite),
                'prix_unitaire': prix,
                'devise_id': self.devise.pk,
            }],
        }
        if caisse:
            payload['type_caisse_id'] = self.caisse.pk
        response = self.client.post('/api/sorties/', payload, format='json')
        self.assertEqual(response.status_code, expect, response.content)
        return Sortie.objects.get(pk=response.json()['id']) if expect == 201 else response

    def annuler(self, kind, obj_id, expect=200, motif='Erreur de saisie'):
        response = self.client.post(f'/api/{kind}/{obj_id}/annuler/', {'motif': motif}, format='json')
        self.assertEqual(response.status_code, expect, response.content)
        return response


class CaisseSortiesTests(MouvementStockBase):
    def test_vente_client_augmente_la_caisse(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        self.assertEqual(self.stock(), D('25'))
        self.assertEqual(self.solde(), D('550'))
        mv = MouvementCaisse.objects.get(sortie=sortie)
        self.assertEqual((mv.type, mv.montant, mv.categorie), ('ENTREE', D('50.00000'), 'VENTE'))

    def test_sorties_non_commerciales_sans_impact_caisse(self):
        self.approvisionner(100)
        motifs = [
            'Produit périmé', 'Produit défectueux', 'Matériel défectueux', 'Perte/Vol', 'Produit volé',
            'Produit endommagé', 'Perte ou destruction', 'Échantillon/Démonstration', 'Cadeau client',
            'Prêt/Formation', 'Casse en entrepôt',
        ]
        stock_attendu = D('100')
        for motif in motifs:
            with self.subTest(motif=motif):
                sortie = self.sortir(2, '10', motif=motif)
                stock_attendu -= 2
                self.assertEqual(self.stock(), stock_attendu)
                self.assertEqual(self.solde(), D('500'))
                self.assertFalse(MouvementCaisse.objects.filter(sortie=sortie).exists())

    def test_sortie_non_commerciale_sans_caisse_selectionnee(self):
        self.approvisionner(10)
        self.sortir(1, motif='Produit périmé', caisse=False)
        self.assertEqual(self.stock(), D('9'))
        self.assertEqual(MouvementCaisse.objects.count(), 0)

    def test_sortie_non_commerciale_a_credit_refusee(self):
        self.approvisionner(10)
        self.sortir(1, motif='Perte/Vol', statut='EN_CREDIT', caisse=False, expect=400)
        self.assertEqual(self.stock(), D('10'))
        self.assertFalse(Sortie.objects.exists())
        self.assertFalse(DettesClients.objects.exists())

    def test_modification_vente_en_sortie_non_commerciale_neutralise_encaissement(self):
        self.approvisionner(10)
        sortie = self.sortir(2, '10')
        self.assertEqual(self.solde(), D('520'))
        response = self.client.patch(
            f'/api/sorties/{sortie.pk}/',
            {
                'motif': 'Produit défectueux', 'statut': 'PAYEE', 'type_caisse_id': self.caisse.pk,
                'lignes': [{'article_id': self.article.pk, 'quantite': '2', 'prix_unitaire': '10', 'devise_id': self.devise.pk}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.solde(), D('500'))
        self.assertEqual(self.stock(), D('8'))

    def test_suppression_sortie_non_commerciale_ne_debite_pas_la_caisse(self):
        self.approvisionner(10)
        sortie = self.sortir(2, motif='Produit périmé')
        response = self.client.delete(f'/api/sorties/{sortie.pk}/', {'type_caisse_id': self.caisse.pk}, format='json')
        self.assertEqual(response.status_code, 204, response.content)
        self.assertEqual(self.solde(), D('500'))
        self.assertEqual(self.stock(), D('10'))

    def test_autres_operations_financieres_inchangees(self):
        response = self.client.post(
            '/api/mouvements-caisse/',
            {'type': 'ENTREE', 'montant': '25', 'devise_id': self.devise.pk, 'type_caisse_id': self.caisse.pk, 'motif': 'Apport'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.solde(), D('525'))


class AnnulationMouvementTests(MouvementStockBase):
    # -- Cas A : approvisionnement ------------------------------------------
    def test_annulation_approvisionnement_paye_restaure_stock_et_caisse(self):
        self.approvisionner(20)
        self.assertEqual((self.stock(), self.solde()), (D('20'), D('500')))
        entree = self.approvisionner(10)
        mv_origine = self.payer_appro(entree, '100')
        self.assertEqual((self.stock(), self.solde()), (D('30'), D('400')))

        diag = self.client.get(f'/api/entrees/{entree.pk}/annulation/')
        self.assertEqual(diag.status_code, 200, diag.content)
        self.assertTrue(diag.json()['possible'])
        self.assertEqual(diag.json()['impact_caisse'][0]['type_annulation'], 'ENTREE')

        body = self.annuler('entrees', entree.pk).json()
        self.assertEqual((self.stock(), self.solde()), (D('20'), D('500')))
        self.assertFalse(Entree.objects.filter(pk=entree.pk).exists())
        self.assertFalse(LigneEntree.objects.filter(entree_id=entree.pk).exists())
        # Historique financier conservé : mouvement d'origine intact + contre-écriture.
        mv_origine.refresh_from_db()
        self.assertEqual((mv_origine.type, mv_origine.montant), ('SORTIE', D('100.00000')))
        contre = MouvementCaisse.objects.get(pk=body['impact_caisse'][0]['mouvement_annulation_id'])
        self.assertEqual((contre.type, contre.montant, contre.categorie), ('ENTREE', D('100.00000'), 'APPROVISIONNEMENT'))
        self.assertEqual(contre.session_caisse_id, self.session.pk)
        annulation = AnnulationMouvement.objects.get()
        self.assertEqual((annulation.type_mouvement, annulation.reference_id), ('ENTREE', entree.pk))
        self.assertEqual(annulation.annule_par, self.admin)
        self.assertEqual(annulation.motif_annulation, 'Erreur de saisie')
        self.assertEqual(annulation.journal['lots'][0]['quantite'], '10.00000')

    def test_annulation_approvisionnement_sans_caisse_ne_cree_aucun_mouvement(self):
        self.approvisionner(20)
        entree = self.approvisionner(10)
        self.annuler('entrees', entree.pk)
        self.assertEqual(self.stock(), D('20'))
        self.assertEqual(MouvementCaisse.objects.count(), 0)

    def test_annulation_approvisionnement_deja_vendu_refusee(self):
        entree = self.approvisionner(10)
        self.sortir(3, '10')
        response = self.annuler('entrees', entree.pk, expect=400)
        self.assertIn('déjà été vendue', response.json()['detail'])
        self.assertIn('(3 unité(s) déjà sorties)', response.json()['detail'])
        self.assertTrue(Entree.objects.filter(pk=entree.pk).exists())
        self.assertEqual((self.stock(), self.solde()), (D('7'), D('530')))
        self.assertFalse(AnnulationMouvement.objects.exists())

    def test_annulation_approvisionnement_issu_de_requisition_la_rend_transformable(self):
        entree = self.approvisionner(10)
        requisition = Requisition.objects.create(
            numero='REQ-T-1', titre='Req test', entreprise=self.entreprise, devise=self.devise, statut=Requisition.STATUT_VALIDEE,
            transformation_status=Requisition.TRANSFO_OUI, transformed_at=timezone.now(),
        )
        entree.source_requisition = requisition
        entree.save(update_fields=['source_requisition'])
        self.annuler('entrees', entree.pk)
        requisition.refresh_from_db()
        self.assertEqual(requisition.transformation_status, Requisition.TRANSFO_NON)
        self.assertTrue(RequisitionHistorique.objects.filter(requisition=requisition, action='ANNULATION_APPROVISIONNEMENT').exists())

    # -- Cas B : vente ----------------------------------------------------------
    def test_annulation_vente_restaure_stock_lots_et_caisse(self):
        entree = self.approvisionner(30)
        sortie = self.sortir(5, '10')
        self.assertEqual((self.stock(), self.solde()), (D('25'), D('550')))
        mv_vente = MouvementCaisse.objects.get(sortie=sortie)

        diag = self.client.get(f'/api/sorties/{sortie.pk}/annulation/').json()
        self.assertEqual(diag['nature'], 'VENTE')
        self.assertEqual(diag['impact_stock'][0]['quantite'], '5.00000')
        self.assertEqual(diag['impact_caisse'][0]['montant'], '50.00000')

        body = self.annuler('sorties', sortie.pk).json()
        self.assertEqual((self.stock(), self.solde()), (D('30'), D('500')))
        lot = LigneEntree.objects.get(entree=entree)
        self.assertEqual(lot.quantite_restante, D('30'))
        self.assertFalse(Sortie.objects.filter(pk=sortie.pk).exists())
        self.assertFalse(LigneSortieLot.objects.exists())
        self.assertFalse(BeneficeLot.objects.exists())
        mv_vente.refresh_from_db()
        self.assertEqual((mv_vente.type, mv_vente.montant), ('ENTREE', D('50.00000')))
        self.assertEqual(MouvementCaisse.objects.count(), 2)
        contre = MouvementCaisse.objects.get(pk=body['impact_caisse'][0]['mouvement_annulation_id'])
        self.assertEqual((contre.type, contre.montant, contre.categorie), ('SORTIE', D('50.00000'), 'VENTE'))
        self.assertEqual(body['nature'], 'VENTE')

    def test_annulation_vente_a_credit_supprime_dette_sans_toucher_caisse(self):
        self.approvisionner(10)
        sortie = self.sortir(2, '10', statut='EN_CREDIT', caisse=False)
        self.assertTrue(DettesClients.objects.filter(sortie=sortie).exists())
        self.annuler('sorties', sortie.pk)
        self.assertEqual((self.stock(), self.solde()), (D('10'), D('500')))
        self.assertFalse(DettesClients.objects.exists())
        self.assertEqual(MouvementCaisse.objects.filter(montant__gt=0).count(), 0)

    def test_annulation_vente_credit_avec_paiements_refusee(self):
        from stock.models import PaiementDettesClients

        self.approvisionner(10)
        sortie = self.sortir(2, '10', statut='EN_CREDIT', caisse=False)
        PaiementDettesClients.objects.create(dettes_clients=sortie.dette_client, montant=D('5'), date=timezone.now().date())
        response = self.annuler('sorties', sortie.pk, expect=400)
        self.assertIn('paiements', response.json()['detail'])
        self.assertTrue(Sortie.objects.filter(pk=sortie.pk).exists())

    def test_annulation_vente_refusee_si_solde_caisse_insuffisant(self):
        self.approvisionner(10)
        sortie = self.sortir(5, '10')
        creer_mouvement_caisse(
            montant=D('520'), devise=self.devise, type_mouvement='SORTIE', entreprise_id=self.entreprise.pk,
            succursale_id=None, type_caisse=self.caisse, motif='Dépôt banque',
        )
        response = self.annuler('sorties', sortie.pk, expect=400)
        self.assertIn('Solde insuffisant', response.json()['detail'])
        self.assertEqual(self.stock(), D('5'))

    def test_annulation_vente_refusee_si_caisse_fermee(self):
        self.approvisionner(10)
        sortie = self.sortir(5, '10')
        self.session.statut = 'CLOTUREE'
        self.session.save(update_fields=['statut'])
        response = self.annuler('sorties', sortie.pk, expect=400)
        self.assertEqual(response.json()['code'], 'annulation_impossible')
        self.assertTrue(Sortie.objects.filter(pk=sortie.pk).exists())

    # -- Cas C : sortie non commerciale ----------------------------------------
    def test_annulation_sortie_non_commerciale_restaure_uniquement_le_stock(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10', motif='Produit périmé')
        self.assertEqual((self.stock(), self.solde()), (D('25'), D('500')))
        diag = self.client.get(f'/api/sorties/{sortie.pk}/annulation/').json()
        self.assertEqual((diag['nature'], diag['impact_caisse']), ('SORTIE_NON_COMMERCIALE', []))
        self.annuler('sorties', sortie.pk)
        self.assertEqual((self.stock(), self.solde()), (D('30'), D('500')))
        self.assertEqual(MouvementCaisse.objects.count(), 0)

    # -- Idempotence, atomicité, sécurité -------------------------------------
    def test_double_annulation_sans_effet_supplementaire(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        self.annuler('sorties', sortie.pk)
        etat = (self.stock(), self.solde(), MouvementCaisse.objects.count())
        response = self.annuler('sorties', sortie.pk, expect=409)
        self.assertIn('a déjà été effectuée', response.json()['detail'])
        self.assertEqual((self.stock(), self.solde(), MouvementCaisse.objects.count()), etat)
        self.assertEqual(AnnulationMouvement.objects.count(), 1)

    def test_echec_en_cours_annulation_ne_laisse_aucune_modification(self):
        entree = self.approvisionner(30)
        sortie = self.sortir(5, '10')
        with mock.patch('caisse.services.caisse.creer_mouvement_caisse', side_effect=CaisseError('Panne caisse simulée')):
            response = self.annuler('sorties', sortie.pk, expect=400)
        self.assertIn('Panne caisse simulée', response.json()['detail'])
        # Le stock avait déjà été restauré avant l'échec : tout doit être revenu en arrière.
        self.assertEqual((self.stock(), self.solde()), (D('25'), D('550')))
        self.assertEqual(LigneEntree.objects.get(entree=entree).quantite_restante, D('25'))
        self.assertTrue(Sortie.objects.filter(pk=sortie.pk).exists())
        self.assertEqual(LigneSortieLot.objects.count(), 1)
        self.assertFalse(AnnulationMouvement.objects.exists())
        # Une nouvelle tentative réussit ensuite normalement.
        self.annuler('sorties', sortie.pk)
        self.assertEqual((self.stock(), self.solde()), (D('30'), D('500')))

    def test_agent_ne_peut_pas_annuler(self):
        self.approvisionner(10)
        sortie = self.sortir(2, '10')
        self.client.force_authenticate(user=self.agent)
        self.annuler('sorties', sortie.pk, expect=403)
        self.assertEqual(self.client.get(f'/api/sorties/{sortie.pk}/annulation/').status_code, 403)
        self.assertTrue(Sortie.objects.filter(pk=sortie.pk).exists())
        self.assertEqual(self.stock(), D('8'))

    def test_isolation_entre_entreprises(self):
        entree = self.approvisionner(10)
        sortie = self.sortir(2, '10')
        autre = self._entreprise('E-Autre', 'autre@example.com')
        intrus = get_user_model().objects.create_user(username='admin_autre', email='autre-admin@example.com', password='x-secret-123')
        Membership.objects.create(user=intrus, entreprise=autre, role='admin', is_active=True)
        self.client.force_authenticate(user=intrus)
        self.annuler('sorties', sortie.pk, expect=404)
        self.annuler('entrees', entree.pk, expect=404)
        self.assertEqual(self.client.get('/api/annulations-mouvements/').json()['count'], 0)
        self.assertEqual(self.stock(), D('8'))

    def test_historique_des_annulations(self):
        self.approvisionner(10)
        sortie = self.sortir(2, '10')
        self.annuler('sorties', sortie.pk)
        data = self.client.get('/api/annulations-mouvements/?type_mouvement=SORTIE').json()
        self.assertEqual(data['count'], 1)
        ligne = data['results'][0]
        self.assertEqual((ligne['reference_id'], ligne['annule_par']), (sortie.pk, self.admin.pk))
        self.assertEqual(ligne['reference_libelle'], f'Vente #{sortie.pk}')

    def test_operations_ulterieures_coherentes_apres_annulation(self):
        """Après annulation, le stock restauré est de nouveau vendable en FIFO depuis le même lot."""
        entree = self.approvisionner(10)
        sortie = self.sortir(10, '10')
        self.assertEqual(self.stock(), D('0'))
        self.annuler('sorties', sortie.pk)
        nouvelle = self.sortir(4, '10')
        self.assertEqual(LigneSortieLot.objects.get(ligne_sortie__sortie=nouvelle).lot_entree.entree_id, entree.pk)
        self.assertEqual((self.stock(), self.solde()), (D('6'), D('540')))
