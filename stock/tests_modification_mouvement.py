"""
Audit des modifications : chaque champ modifiable d'une vente ou d'un approvisionnement
garde stock, caisse, client, dette et historique cohérents. Rapports commerciaux et page Audit.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from caisse.models import MouvementCaisse, SessionCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse
from stock.models import (
    AnnulationMouvement,
    BeneficeLot,
    Client,
    ClientEntreprise,
    DettesClients,
    Entree,
    InventaireLigne,
    InventaireSession,
    LigneEntree,
    LigneSortie,
    LigneSortieLot,
    LogSuppression,
    ModificationMouvement,
    PaiementDettesClients,
    Sortie,
)
from stock.tests_annulation_mouvement import MouvementStockBase
from users.models import Membership

D = Decimal


class ModificationBase(MouvementStockBase):
    def modifier(self, sortie, *, quantite='5', prix='10', motif='Vente au Client', statut='PAYEE',
                 caisse=None, client='default', expect=200, extra=None):
        payload = {
            'motif': motif,
            'statut': statut,
            'lignes': [{
                'article_id': self.article.pk, 'quantite': str(quantite), 'prix_unitaire': prix,
                'devise_id': self.devise.pk,
            }],
        }
        payload['client_id'] = self.client_fiche.pk if client == 'default' else client
        if caisse is not None:
            payload['type_caisse_id'] = caisse
        payload.update(extra or {})
        response = self.client.patch(f'/api/sorties/{sortie.pk}/', payload, format='json')
        self.assertEqual(response.status_code, expect, response.content)
        return response

    def net_caisse(self, sortie_id, caisse=None):
        qs = MouvementCaisse.objects.filter(reference_piece__contains=f'VENT-{sortie_id}-')
        if caisse is not None:
            qs = qs.filter(type_caisse=caisse)
        return sum((m.montant if m.type == 'ENTREE' else -m.montant for m in qs), D('0'))

    def cloturer_et_rouvrir(self):
        self.session.statut = 'CLOTUREE'
        self.session.cloture_le = timezone.now()
        self.session.save(update_fields=['statut', 'cloture_le'])
        self.session = SessionCaisse.objects.create(
            numero='TEST-ANNUL-SESSION-2', type_caisse=self.caisse, devise=self.devise, entreprise=self.entreprise,
            ouvert_le=timezone.now(), solde_ouverture=D('0'), statut='OUVERTE',
        )


class ModificationVenteTests(ModificationBase):
    def test_quantite_session_ouverte_corrige_encaissement_et_conserve_la_date(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        date_vente = LigneSortie.objects.get(sortie=sortie).date_sortie
        self.modifier(sortie, quantite='3')
        self.assertEqual((self.stock(), self.solde()), (D('27'), D('530')))
        self.assertEqual(MouvementCaisse.objects.filter(sortie=sortie).count(), 1)
        self.assertEqual(LigneSortie.objects.get(sortie=sortie).date_sortie, date_vente)
        modif = ModificationMouvement.objects.get()
        self.assertTrue(any('quantité 5 → 3' in c for c in modif.changements), modif.changements)
        self.assertTrue(modif.sensible)

    def test_session_cloturee_jamais_reecrite_ajustement_dans_session_ouverte(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        mv = MouvementCaisse.objects.get(sortie=sortie)
        ancienne = self.session
        self.cloturer_et_rouvrir()
        self.modifier(sortie, quantite='3', caisse=self.caisse.pk, expect=400)  # solde nouvelle session = 0
        creer_mouvement_caisse(
            montant=D('100'), devise=self.devise, type_mouvement='ENTREE', entreprise_id=self.entreprise.pk,
            succursale_id=None, type_caisse=self.caisse, motif='Fond de caisse',
        )
        self.modifier(sortie, quantite='3', caisse=self.caisse.pk)
        mv.refresh_from_db()
        self.assertEqual((mv.montant, mv.session_caisse_id), (D('50.00000'), ancienne.pk))
        ajustement = MouvementCaisse.objects.get(reference_piece=f'AJ-VENT-{sortie.pk}-USD-1')
        self.assertEqual((ajustement.type, ajustement.montant), ('SORTIE', D('20.00000')))
        self.assertEqual(ajustement.session_caisse_id, self.session.pk)
        self.assertEqual(self.net_caisse(sortie.pk), D('30'))

    def test_passage_au_credit_neutralise_la_caisse_et_cree_la_dette(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        self.modifier(sortie, statut='EN_CREDIT')
        self.assertEqual(self.solde(), D('500'))
        self.assertEqual(DettesClients.objects.get(sortie=sortie).montant, D('50.00000'))
        self.assertTrue(ModificationMouvement.objects.get().sensible)

    def test_retour_au_comptant_refuse_si_paiements(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10', statut='EN_CREDIT', caisse=False)
        PaiementDettesClients.objects.create(dettes_clients=sortie.dette_client, montant=D('10'), date=timezone.localdate())
        response = self.modifier(sortie, statut='PAYEE', caisse=self.caisse.pk, expect=400)
        self.assertIn('paiements ont déjà été reçus', response.json()['detail'])
        self.assertEqual(self.solde(), D('500'))

    def test_retour_au_comptant_sans_paiement_encaisse_et_supprime_la_dette(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10', statut='EN_CREDIT', caisse=False)
        self.modifier(sortie, statut='PAYEE', caisse=self.caisse.pk)
        self.assertEqual(self.solde(), D('550'))
        self.assertFalse(DettesClients.objects.filter(sortie=sortie).exists())

    def test_credit_avec_paiement_suit_le_nouveau_total(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10', statut='EN_CREDIT', caisse=False)
        PaiementDettesClients.objects.create(dettes_clients=sortie.dette_client, montant=D('20'), date=timezone.localdate())
        self.modifier(sortie, quantite='6', statut='EN_CREDIT')
        dette = DettesClients.objects.get(sortie=sortie)
        self.assertEqual((dette.montant, dette.paye, dette.reste), (D('60.00000'), D('20.00000'), D('40.00000')))
        response = self.modifier(sortie, quantite='1', statut='EN_CREDIT', expect=400)
        self.assertIn('inférieur aux paiements', response.json()['detail'])
        self.assertEqual(self.stock(), D('24'))

    def test_changement_de_client(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10', statut='EN_CREDIT', caisse=False)
        autre = Client.objects.create(id='CLI-AUTRE', nom='Autre client')
        ClientEntreprise.objects.create(client=autre, entreprise=self.entreprise)
        etranger = Client.objects.create(id='CLI-ETR', nom='Client étranger')
        self.modifier(sortie, statut='EN_CREDIT', client=etranger.pk, expect=400)
        PaiementDettesClients.objects.create(dettes_clients=sortie.dette_client, montant=D('5'), date=timezone.localdate())
        response = self.modifier(sortie, statut='EN_CREDIT', client=autre.pk, expect=400)
        self.assertIn('changer le client', response.json()['detail'])
        PaiementDettesClients.objects.all().delete()
        self.modifier(sortie, statut='EN_CREDIT', client=autre.pk)
        self.assertEqual(Sortie.objects.get(pk=sortie.pk).client_id, autre.pk)

    def test_vente_devenue_non_commerciale_puis_vente(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        self.modifier(sortie, motif='Produit périmé')
        sortie.refresh_from_db()
        self.assertFalse(sortie.est_commerciale)
        self.assertEqual((self.solde(), self.stock()), (D('500'), D('25')))
        self.modifier(sortie, motif='Vente au Client', caisse=self.caisse.pk)
        sortie.refresh_from_db()
        self.assertTrue(sortie.est_commerciale)
        self.assertEqual(self.solde(), D('550'))

    def test_changement_de_caisse_transfere_l_encaissement(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        banque = TypeCaisse.objects.create(
            nom='Banque', libelle='Banque', code_type='BANQUE', devise=self.devise,
            entreprise=self.entreprise, is_active=True, est_defaut=False,
        )
        self.modifier(sortie, caisse=banque.pk)
        self.assertEqual(self.net_caisse(sortie.pk, self.caisse), D('0'))
        self.assertEqual(self.net_caisse(sortie.pk, banque), D('50'))
        self.assertEqual(self.solde(), D('500'))

    def test_remboursement_refuse_si_solde_insuffisant(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        creer_mouvement_caisse(
            montant=D('540'), devise=self.devise, type_mouvement='SORTIE', entreprise_id=self.entreprise.pk,
            succursale_id=None, type_caisse=self.caisse, motif='Dépôt banque',
        )
        response = self.modifier(sortie, quantite='1', expect=400)
        self.assertIn('Solde insuffisant', response.json()['detail'])
        self.assertEqual((self.stock(), self.solde()), (D('25'), D('10')))
        self.assertFalse(ModificationMouvement.objects.exists())

    def test_agent_ne_peut_pas_modifier(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        self.client.force_authenticate(user=self.agent)
        self.modifier(sortie, quantite='1', expect=403)
        self.assertEqual(self.stock(), D('25'))

    def test_modification_refusee_apres_inventaire_valide(self):
        self.approvisionner(30)
        sortie = self.sortir(5, '10')
        inventaire = InventaireSession.objects.create(
            libelle='Inventaire', date_inventaire=timezone.localdate(), statut=InventaireSession.STATUT_VALIDE,
            entreprise=self.entreprise, date_validation=timezone.now(),
        )
        InventaireLigne.objects.create(session=inventaire, article=self.article)
        response = self.modifier(sortie, quantite='1', expect=400)
        self.assertIn('inventaire', response.json()['detail'])

    def test_sortie_d_ajustement_inventaire_non_modifiable(self):
        self.approvisionner(30)
        sortie = self.sortir(2, '10', motif='Ajustement inventaire #1', caisse=False)
        InventaireSession.objects.create(
            libelle='Inventaire', date_inventaire=timezone.localdate(), statut=InventaireSession.STATUT_VALIDE,
            entreprise=self.entreprise, sortie_ajustement=sortie,
        )
        response = self.modifier(sortie, quantite='1', motif='Ajustement inventaire #1', expect=400)
        self.assertIn("ajustement d'inventaire", response.json()['detail'])

    def test_retrait_d_un_article_journalise(self):
        from stock.models import Article

        autre = Article.objects.create(
            nom_scientifique='Brosse', nom_commercial='Brosse', sous_type_article=self.article.sous_type_article,
            unite=self.article.unite, emplacement='A2', entreprise=self.entreprise,
        )
        self.approvisionner(30)
        response = self.client.post('/api/entrees/', {'libele': 'Appro brosse', 'lignes': [{
            'article_id': autre.pk, 'quantite': '10', 'prix_unitaire': '2', 'prix_vente': '10',
            'devise_id': self.devise.pk, 'seuil_alerte': '0',
        }]}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        created = self.client.post('/api/sorties/', {
            'motif': 'Vente au Client', 'statut': 'PAYEE', 'type_caisse_id': self.caisse.pk,
            'lignes': [
                {'article_id': self.article.pk, 'quantite': '2', 'prix_unitaire': '10', 'devise_id': self.devise.pk},
                {'article_id': autre.pk, 'quantite': '1', 'prix_unitaire': '10', 'devise_id': self.devise.pk},
            ],
        }, format='json')
        sortie = Sortie.objects.get(pk=created.json()['id'])
        self.modifier(sortie, quantite='2')
        log = LogSuppression.objects.get()
        self.assertEqual((log.article_id, log.motif), (autre.pk, LogSuppression.MOTIF_LIGNE))
        self.assertEqual(self.solde(), D('520'))


class ModificationApprovisionnementTests(ModificationBase):
    def _patch_entree(self, entree, ligne, expect=200, **champs):
        valeurs = {'id': ligne.pk, 'article_id': self.article.pk, 'quantite': '10', 'prix_unitaire': '2',
                   'prix_vente': '10', 'devise_id': self.devise.pk, 'seuil_alerte': '0'}
        valeurs.update(champs)
        response = self.client.patch(
            f'/api/entrees/{entree.pk}/', {'libele': entree.libele, 'lignes': [valeurs]}, format='json',
        )
        self.assertEqual(response.status_code, expect, response.content)
        return response

    def test_correction_prix_achat_repercutee_sur_les_ventes(self):
        entree = self.approvisionner(10, prix_achat='2')
        sortie = self.sortir(4, '10')
        ligne = LigneEntree.objects.get(entree=entree)
        self._patch_entree(entree, ligne, prix_unitaire='3')
        self.assertEqual(LigneSortieLot.objects.get(ligne_sortie__sortie=sortie).prix_achat, D('3.00000'))
        benefice = BeneficeLot.objects.get(ligne_sortie__sortie=sortie)
        self.assertEqual(benefice.benefice_total, D('28.00000'))  # 40 - 4 × 3
        modif = ModificationMouvement.objects.get(type_mouvement='ENTREE')
        self.assertTrue(modif.sensible)
        self.assertTrue(any("prix d'achat 2 USD → 3 USD" in c for c in modif.changements), modif.changements)

    def test_quantite_sous_le_vendu_refusee(self):
        entree = self.approvisionner(10)
        self.sortir(4, '10')
        self._patch_entree(entree, LigneEntree.objects.get(entree=entree), quantite='3', expect=400)
        self.assertEqual(self.stock(), D('6'))

    def test_prix_achat_negatif_refuse(self):
        entree = self.approvisionner(10)
        self._patch_entree(entree, LigneEntree.objects.get(entree=entree), prix_unitaire='-1', expect=400)

    def test_quantite_bloquee_apres_inventaire_mais_libelle_modifiable(self):
        entree = self.approvisionner(10)
        inventaire = InventaireSession.objects.create(
            libelle='Inventaire', date_inventaire=timezone.localdate(), statut=InventaireSession.STATUT_VALIDE,
            entreprise=self.entreprise, date_validation=timezone.now(),
        )
        InventaireLigne.objects.create(session=inventaire, article=self.article)
        ligne = LigneEntree.objects.get(entree=entree)
        self._patch_entree(entree, ligne, quantite='12', expect=400)
        response = self.client.patch(f'/api/entrees/{entree.pk}/', {'libele': 'Nouveau libellé'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.stock(), D('10'))

    def test_suppression_approvisionnement_tracee_ou_refusee(self):
        consomme = self.approvisionner(10)
        self.sortir(2, '10')
        self.assertEqual(self.client.delete(f'/api/entrees/{consomme.pk}/').status_code, 400)
        intact = self.approvisionner(5)
        self.assertEqual(self.client.delete(f'/api/entrees/{intact.pk}/').status_code, 204)
        self.assertTrue(AnnulationMouvement.objects.filter(type_mouvement='ENTREE', reference_id=intact.pk).exists())
        self.assertEqual(self.stock(), D('8'))

    def test_agent_ne_peut_pas_modifier(self):
        entree = self.approvisionner(10)
        self.client.force_authenticate(user=self.agent)
        self._patch_entree(entree, LigneEntree.objects.get(entree=entree), quantite='20', expect=403)


class RapportsCommerciauxTests(ModificationBase):
    def test_rapport_ventes_session_uniquement_commercial(self):
        self.approvisionner(50)
        self.sortir(5, '10')
        self.sortir(3, '10', motif='Produit périmé')
        self.sortir(2, '10', motif='Perte/Vol')
        response = self.client.get('/api/rapports/ventes/', {'session_id': self.session.pk})
        self.assertEqual(response.status_code, 200, response.content)
        resume = response.json()['resume_global']
        self.assertEqual(resume['nombre_ventes'], 1)
        self.assertEqual(D(resume['total_general']), D('50'))
        self.assertEqual(D(resume['total_quantite']), D('5'))

    def test_benefices_uniquement_commercial(self):
        self.approvisionner(50, prix_achat='2')
        self.sortir(5, '10')
        self.sortir(3, '10', motif='Produit défectueux')
        now = timezone.now()
        response = self.client.get('/api/entrees/benefices-totaux/', {'year': now.year, 'month': now.month})
        self.assertEqual(response.status_code, 200, response.content)
        # 5 vendus × (10 − 2) ; la sortie « défectueux » (3 unités) n'est pas un bénéfice.
        self.assertEqual(D(response.json()['resume']['benefice_total']), D('40'))

    def test_liste_des_sorties_expose_la_nature(self):
        self.approvisionner(10)
        sortie = self.sortir(1, '10', motif='Cadeau client')
        data = self.client.get(f'/api/sorties/{sortie.pk}/').json()
        self.assertFalse(data['est_commerciale'])


class AuditTests(ModificationBase):
    def test_audit_regroupe_les_mouvements_suspects(self):
        self.approvisionner(50, prix_achat='2')
        vente = self.sortir(5, '10')
        self.sortir(2, '10', motif='Perte/Vol')
        self.modifier(vente, quantite='4')
        annulee = self.sortir(1, '10')
        self.annuler('sorties', annulee.pk, motif='')
        creer_mouvement_caisse(
            montant=D('15'), devise=self.devise, type_mouvement='SORTIE', entreprise_id=self.entreprise.pk,
            succursale_id=None, type_caisse=self.caisse, motif='', categorie='SORTIE_MANUELLE',
        )
        response = self.client.get('/api/audit/mouvements/')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        par_code = {c['code']: c for c in data['categories']}
        self.assertEqual(par_code['PERTE']['nombre'], 1)
        self.assertEqual(par_code['PERTE']['montants'], {'USD': '4.00'})  # 2 × coût 2
        self.assertEqual(par_code['MODIFICATION']['nombre'], 1)
        self.assertEqual(par_code['ANNULATION']['nombre'], 1)
        self.assertEqual(par_code['RETRAIT_CAISSE']['nombre'], 1)
        self.assertTrue(all(c['explication'] for c in data['categories']))
        perte = next(e for e in data['evenements'] if e['categorie'] == 'PERTE')
        self.assertEqual(perte['gravite'], 'HAUTE')
        self.assertEqual(perte['utilisateur'], 'admin_annul')  # créateur de la sortie tracé
        filtre = self.client.get('/api/audit/mouvements/', {'categorie': 'PERTE'}).json()
        self.assertEqual(filtre['total'], 1)

    def test_audit_reserve_aux_admins_et_isole(self):
        self.approvisionner(10)
        self.sortir(1, '10', motif='Perte/Vol')
        self.client.force_authenticate(user=self.agent)
        self.assertEqual(self.client.get('/api/audit/mouvements/').status_code, 403)
        autre = self._entreprise('E-Audit-Autre', 'audit-autre@example.com')
        intrus = get_user_model().objects.create_user(username='admin_audit', email='a-audit@example.com', password='x-secret-123')
        Membership.objects.create(user=intrus, entreprise=autre, role='admin', is_active=True)
        self.client.force_authenticate(user=intrus)
        self.assertEqual(self.client.get('/api/audit/mouvements/').json()['total'], 0)

    def test_audit_dates_invalides(self):
        self.assertEqual(self.client.get('/api/audit/mouvements/', {'date_debut': '2026-13-01'}).status_code, 400)
        self.assertEqual(
            self.client.get('/api/audit/mouvements/', {'date_debut': '2026-05-02', 'date_fin': '2026-05-01'}).status_code,
            400,
        )
