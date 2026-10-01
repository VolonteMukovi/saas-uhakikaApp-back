"""
Annulation d'un inventaire déjà validé : restauration exacte de la situation antérieure.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from caisse.models import TypeCaisse
from stock.models import (
    Article,
    BeneficeLot,
    Devise,
    Entree,
    Entreprise,
    InventaireSession,
    LigneEntree,
    LigneSortieLot,
    Sortie,
    SousTypeArticle,
    Stock,
    TypeArticle,
    Unite,
)
from stock.services.inventaire_annulation import annuler_validation_session
from users.models import Membership

D = Decimal


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class InventaireAnnulationTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-ANNUL', secteur='s', pays='CD', adresse='a', telephone='t',
            email='annul@example.com', nif='n-annul', responsable='resp',
        )
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin_annul', email='annul@example.com', password='secretpass123',
        )
        Membership.objects.create(user=self.admin, entreprise=self.entreprise, role='admin', is_active=True)
        self.agent = User.objects.create_user(
            username='agent_annul', email='agent_annul@example.com', password='secretpass123',
        )
        Membership.objects.create(user=self.agent, entreprise=self.entreprise, role='user', is_active=True)
        self.client.force_authenticate(user=self.admin)

        self.devise = Devise.objects.create(
            sigle='USD', nom='Dollar', symbole='$', est_principal=True, entreprise=self.entreprise,
        )
        self.caisse = TypeCaisse.objects.create(
            nom='Caisse', libelle='Caisse', code_type='BANQUE', entreprise=self.entreprise,
            devise=self.devise, is_active=True,
        )
        self.unite = Unite.objects.create(libelle='pcs', entreprise=self.entreprise)
        type_art = TypeArticle.objects.create(libelle='Produit', entreprise=self.entreprise)
        self.sous = SousTypeArticle.objects.create(
            libelle='Divers', type_article=type_art, entreprise=self.entreprise,
        )
        # Article A : deux lots FIFO (prix différents), 75 en stock.
        self.article_a = self._article('Article A')
        self.lot_a1 = self._lot(self.article_a, quantite='50', restante='25', prix='0.01')
        self.lot_a2 = self._lot(self.article_a, quantite='50', restante='50', prix='0.02')
        Stock.objects.create(article=self.article_a, Qte=D('75'), seuilAlert=D('5'))
        # Article B : un lot, 40 en stock.
        self.article_b = self._article('Article B')
        self.lot_b1 = self._lot(self.article_b, quantite='40', restante='40', prix='1.5')
        Stock.objects.create(article=self.article_b, Qte=D('40'), seuilAlert=D('0'))

    # --- utilitaires ---------------------------------------------------------

    def _article(self, nom):
        return Article.objects.create(
            nom_scientifique=nom, nom_commercial=nom, sous_type_article=self.sous,
            unite=self.unite, entreprise=self.entreprise,
        )

    def _lot(self, article, *, quantite, restante, prix):
        entree = Entree.objects.create(libele=f'Appro {article.nom_scientifique}', entreprise=self.entreprise)
        return LigneEntree.objects.create(
            article=article, entree=entree, quantite=D(quantite), quantite_restante=D(restante),
            prix_unitaire=D(prix), prix_vente=D(prix) * 2, devise=self.devise,
        )

    def _etat(self):
        """Photographie de tout ce que la validation peut modifier."""
        return {
            'stocks': {s.article_id: s.Qte for s in Stock.objects.order_by('article_id')},
            'lots': {
                l.pk: (l.quantite, l.quantite_restante, l.prix_unitaire)
                for l in LigneEntree.objects.order_by('pk')
            },
            'sorties': set(Sortie.objects.values_list('pk', flat=True)),
            'entrees': set(Entree.objects.values_list('pk', flat=True)),
            'benefices': BeneficeLot.objects.count(),
            'traces': LigneSortieLot.objects.count(),
            'valorisation': sum(
                (l.quantite_restante * l.prix_unitaire for l in LigneEntree.objects.all()),
                D('0'),
            ),
        }

    def _inventaire_valide(self, physiques: dict, libelle='Inventaire'):
        create = self.client.post('/api/inventaires/', {
            'libelle': libelle,
            'date_inventaire': timezone.now().date().isoformat(),
            'perimetre': 'EN_STOCK',
            'demarrer': True,
        }, format='json')
        self.assertEqual(create.status_code, 201, create.content)
        sid = create.json()['id']
        bulk = self.client.post(f'/api/inventaires/{sid}/lignes/bulk/', {'lignes': [
            {'article_id': a.article_id, 'stock_physique': str(q)} for a, q in physiques.items()
        ]}, format='json')
        self.assertEqual(bulk.status_code, 200, bulk.content)
        valide = self.client.post(f'/api/inventaires/{sid}/valider/', {}, format='json')
        self.assertEqual(valide.status_code, 200, valide.content)
        return InventaireSession.objects.get(pk=sid)

    def _annuler(self, session, **body):
        return self.client.post(f'/api/inventaires/{session.pk}/annuler/', body, format='json')

    # --- cas rencontré : validation avec tous les stocks physiques à 0 -------

    def test_annulation_validation_a_zero_restaure_exactement(self):
        avant = self._etat()
        session = self._inventaire_valide({self.article_a: 0, self.article_b: 0})
        self.assertEqual(Stock.objects.get(article=self.article_a).Qte, D('0'))
        self.assertIsNotNone(session.sortie_ajustement_id)
        sortie_id = session.sortie_ajustement_id

        resp = self._annuler(session, motif='Validé sans comptage')
        self.assertEqual(resp.status_code, 200, resp.content)

        self.assertEqual(self._etat(), avant)
        self.assertFalse(Sortie.objects.filter(pk=sortie_id).exists())
        session.refresh_from_db()
        self.assertEqual(session.statut, InventaireSession.STATUT_ANNULE)
        self.assertTrue(session.validation_annulee)
        self.assertEqual(session.annule_par, self.admin)
        self.assertIsNotNone(session.date_annulation)
        self.assertEqual(session.motif_annulation, 'Validé sans comptage')
        self.assertEqual(session.journal_annulation['sortie_ajustement']['id'], sortie_id)
        self.assertEqual(len(session.journal_annulation['sortie_ajustement']['lignes']), 2)
        # Historique de l'inventaire conservé (lignes et valeurs saisies).
        self.assertEqual(session.lignes.count(), 2)
        self.assertIsNotNone(session.date_validation)

    def test_annulation_ecarts_mixtes_retire_entree_et_restaure_sortie(self):
        avant = self._etat()
        session = self._inventaire_valide({self.article_a: 70, self.article_b: 45})
        self.assertIsNotNone(session.entree_ajustement_id)
        self.assertIsNotNone(session.sortie_ajustement_id)
        entree_id = session.entree_ajustement_id

        resp = self._annuler(session)
        self.assertEqual(resp.status_code, 200, resp.content)

        self.assertEqual(self._etat(), avant)
        self.assertFalse(Entree.objects.filter(pk=entree_id).exists())
        data = resp.json()
        self.assertEqual(data['statut'], 'ANNULE')
        self.assertTrue(data['validation_annulee'])
        self.assertEqual(data['annule_par_nom'], 'admin_annul')

    # --- refus ---------------------------------------------------------------

    def test_double_annulation_refusee(self):
        session = self._inventaire_valide({self.article_a: 0, self.article_b: 0})
        self.assertEqual(self._annuler(session).status_code, 200)
        etat = self._etat()
        resp = self._annuler(session)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(self._etat(), etat)

    def test_inventaire_inexistant(self):
        resp = self.client.post('/api/inventaires/999999/annuler/', {}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_inventaire_brouillon_annulation_simple_inchangee(self):
        create = self.client.post('/api/inventaires/', {
            'libelle': 'Brouillon', 'date_inventaire': timezone.now().date().isoformat(),
        }, format='json')
        sid = create.json()['id']
        resp = self.client.post(f'/api/inventaires/{sid}/annuler/', {}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        session = InventaireSession.objects.get(pk=sid)
        self.assertEqual(session.statut, InventaireSession.STATUT_ANNULE)
        self.assertFalse(session.validation_annulee)

    def test_agent_ne_peut_pas_annuler_un_inventaire_valide(self):
        session = self._inventaire_valide({self.article_a: 0, self.article_b: 0})
        etat = self._etat()
        self.client.force_authenticate(user=self.agent)
        resp = self._annuler(session)
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(self._etat(), etat)
        diag = self.client.get(f'/api/inventaires/{session.pk}/annulation-validation/').json()
        self.assertFalse(diag['autorise'])

    def test_autre_entreprise_ne_voit_pas_l_inventaire(self):
        session = self._inventaire_valide({self.article_a: 0, self.article_b: 0})
        autre = Entreprise.objects.create(
            nom='Autre', secteur='s', pays='CD', adresse='a', telephone='t',
            email='autre@example.com', nif='n-autre', responsable='r',
        )
        intrus = get_user_model().objects.create_user(username='intrus', password='secretpass123')
        Membership.objects.create(user=intrus, entreprise=autre, role='admin', is_active=True)
        self.client.force_authenticate(user=intrus)
        self.assertEqual(self._annuler(session).status_code, 404)

    def test_refus_si_stock_ajoute_par_l_inventaire_a_ete_vendu(self):
        # +10 sur B (lot d'ajustement créé), puis une vente consomme ce lot.
        session = self._inventaire_valide({self.article_a: 75, self.article_b: 50})
        vente = self.client.post('/api/sorties/', {
            'statut': 'PAYEE',
            'type_caisse_id': self.caisse.pk,
            'lignes': [{'article_id': self.article_b.pk, 'quantite': '45',
                        'prix_unitaire': '3', 'devise_id': self.devise.pk}],
        }, format='json')
        self.assertEqual(vente.status_code, 201, vente.content)
        etat = self._etat()

        resp = self._annuler(session)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn('déjà été vendu', resp.json()['detail'])
        self.assertEqual(self._etat(), etat)
        session.refresh_from_db()
        self.assertEqual(session.statut, InventaireSession.STATUT_VALIDE)

    def test_refus_si_inventaire_ulterieur_valide_sur_memes_articles(self):
        premier = self._inventaire_valide({self.article_a: 0, self.article_b: 0}, 'Premier')
        # Restocker pour pouvoir lancer un second inventaire "en stock".
        self._lot(self.article_a, quantite='10', restante='10', prix='0.01')
        Stock.objects.filter(article=self.article_a).update(Qte=D('10'))
        self._inventaire_valide({self.article_a: 8}, 'Second')
        etat = self._etat()

        resp = self._annuler(premier)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn('Second', resp.json()['detail'])
        self.assertEqual(self._etat(), etat)

    # --- opérations indépendantes et ultérieures -----------------------------

    def test_vente_independante_ulterieure_preservee(self):
        session = self._inventaire_valide({self.article_a: 75, self.article_b: 30})
        # Vente après validation, sur l'article A (non touché par les ajustements).
        vente = self.client.post('/api/sorties/', {
            'statut': 'PAYEE',
            'type_caisse_id': self.caisse.pk,
            'lignes': [{'article_id': self.article_a.pk, 'quantite': '30',
                        'prix_unitaire': '1', 'devise_id': self.devise.pk}],
        }, format='json')
        self.assertEqual(vente.status_code, 201, vente.content)
        vente_id = vente.json()['id']
        traces_vente = LigneSortieLot.objects.filter(ligne_sortie__sortie_id=vente_id).count()

        resp = self._annuler(session)
        self.assertEqual(resp.status_code, 200, resp.content)

        self.assertTrue(Sortie.objects.filter(pk=vente_id).exists())
        self.assertEqual(LigneSortieLot.objects.filter(ligne_sortie__sortie_id=vente_id).count(), traces_vente)
        self.assertEqual(Stock.objects.get(article=self.article_a).Qte, D('45'))  # 75 - 30
        self.assertEqual(Stock.objects.get(article=self.article_b).Qte, D('40'))  # restauré

    def test_inventaire_en_cours_demarre_apres_est_recalcule(self):
        erreur = self._inventaire_valide({self.article_a: 0, self.article_b: 0}, 'Erreur')
        # Nouvel inventaire démarré sur le stock faussé (théorique figé à 0).
        create = self.client.post('/api/inventaires/', {
            'libelle': 'Correction', 'date_inventaire': timezone.now().date().isoformat(),
            'perimetre': 'COMPLET', 'demarrer': True,
        }, format='json')
        self.assertEqual(create.status_code, 201, create.content)
        correction = InventaireSession.objects.get(pk=create.json()['id'])
        ligne_a = correction.lignes.get(article=self.article_a)
        self.assertEqual(ligne_a.stock_theorique, D('0'))
        self.client.patch(
            f'/api/inventaires/{correction.pk}/lignes/{ligne_a.pk}/',
            {'stock_physique': '70'}, format='json',
        )

        diag = self.client.get(f'/api/inventaires/{erreur.pk}/annulation-validation/').json()
        self.assertTrue(diag['possible'], diag)
        self.assertEqual(diag['impact']['inventaires_en_cours_recalcules'], [correction.pk])

        self.assertEqual(self._annuler(erreur).status_code, 200)

        ligne_a.refresh_from_db()
        self.assertEqual(ligne_a.stock_theorique, D('75'))
        self.assertEqual(ligne_a.ecart, D('-5'))
        self.assertEqual(correction.lignes.get(article=self.article_b).stock_theorique, D('40'))

    # --- robustesse ----------------------------------------------------------

    def test_erreur_en_cours_d_annulation_ne_laisse_rien_de_partiel(self):
        session = self._inventaire_valide({self.article_a: 0, self.article_b: 0})
        etat = self._etat()
        from stock.services import inventaire_annulation

        vrai_apply = inventaire_annulation.apply_stock_delta
        appels = {'n': 0}

        def apply_qui_echoue(*args, **kwargs):
            appels['n'] += 1
            if appels['n'] == 2:
                raise RuntimeError('panne simulée')
            return vrai_apply(*args, **kwargs)

        with patch.object(inventaire_annulation, 'apply_stock_delta', side_effect=apply_qui_echoue):
            with self.assertRaises(RuntimeError):
                annuler_validation_session(session, self.admin)

        self.assertEqual(self._etat(), etat)
        session.refresh_from_db()
        self.assertEqual(session.statut, InventaireSession.STATUT_VALIDE)
        self.assertFalse(session.validation_annulee)

    def test_diagnostic_et_affichage_apres_annulation(self):
        session = self._inventaire_valide({self.article_a: 0, self.article_b: 0})
        diag = self.client.get(f'/api/inventaires/{session.pk}/annulation-validation/').json()
        self.assertTrue(diag['possible'])
        self.assertTrue(diag['autorise'])
        self.assertEqual(diag['impact']['articles_restaures'], 2)
        self.assertEqual(D(diag['impact']['quantite_restauree']), D('115'))

        self._annuler(session)
        detail = self.client.get(f'/api/inventaires/{session.pk}/').json()
        self.assertEqual(detail['statut'], 'ANNULE')
        self.assertTrue(detail['validation_annulee'])
        self.assertIsNone(detail['sortie_ajustement_id'])
        diag = self.client.get(f'/api/inventaires/{session.pk}/annulation-validation/').json()
        self.assertFalse(diag['possible'])
        stocks = {
            row['article']['article_id'] if isinstance(row.get('article'), dict) else row.get('article_id'): row
            for row in self.client.get('/api/stocks/').json().get('results', [])
        }
        self.assertTrue(stocks)
        # Suppression interdite : la trace de l'inventaire validé puis annulé est conservée.
        self.assertEqual(self.client.delete(f'/api/inventaires/{session.pk}/').status_code, 400)

    def test_service_refuse_un_inventaire_non_valide(self):
        create = self.client.post('/api/inventaires/', {
            'libelle': 'Brouillon', 'date_inventaire': timezone.now().date().isoformat(),
        }, format='json')
        session = InventaireSession.objects.get(pk=create.json()['id'])
        with self.assertRaises(ValidationError):
            annuler_validation_session(session, self.admin)
