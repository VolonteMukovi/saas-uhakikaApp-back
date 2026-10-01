"""
Annulation d'un inventaire déjà validé.

La validation (stock.services.inventaire.valider_session) produit au plus :
- une Sortie d'ajustement (écarts négatifs) : lots FIFO consommés, LigneSortie,
  LigneSortieLot, BeneficeLot et Stock.Qte diminué ;
- une Entree d'ajustement (écarts positifs) : nouveaux lots LigneEntree et Stock.Qte augmenté.
Aucun mouvement de caisse ni dette n'est généré.

L'annulation remet exactement chaque lot consommé dans son état antérieur (même lot,
même date, même prix), retire les lots créés, puis supprime les deux pièces
d'ajustement, comme la suppression d'une vente (rollback_sortie_ligne). Une
contre-écriture laisserait au contraire les lots d'origine épuisés et fausserait la
valorisation FIFO et les bénéfices. Le détail de ce qui a été annulé est conservé
dans InventaireSession.journal_annulation.

L'annulation est refusée dès qu'une opération ultérieure dépend de ces ajustements
(lot d'ajustement déjà vendu, inventaire validé plus tard…), plutôt que de modifier
des données qui ne lui appartiennent pas.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from stock.models import (
    BeneficeLot,
    DettesClients,
    Entree,
    InventaireLigne,
    InventaireSession,
    LigneEntree,
    LigneSortie,
    LigneSortieLot,
    Sortie,
)
from stock.services.stock_adjustment import apply_stock_delta

MAX_ARTICLES_CITES = 10


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.00001'))


def _nom_article(article) -> str:
    return article.nom_commercial or article.nom_scientifique or article.article_id


def _citer(noms: list[str]) -> str:
    extrait = ', '.join(noms[:MAX_ARTICLES_CITES])
    if len(noms) > MAX_ARTICLES_CITES:
        extrait += f' … (+{len(noms) - MAX_ARTICLES_CITES})'
    return extrait


def _lignes_sortie(sortie: Sortie, *, verrou: bool = False) -> list[LigneSortie]:
    lots_qs = LigneSortieLot.objects.select_related('lot_entree')
    qs = LigneSortie.objects.filter(sortie=sortie).select_related('article')
    if verrou:
        qs = qs.select_for_update()
    return list(qs.prefetch_related(Prefetch('lots_utilises', queryset=lots_qs)).order_by('id'))


def _lots_entree(entree: Entree, *, verrou: bool = False) -> list[LigneEntree]:
    qs = LigneEntree.objects.filter(entree=entree).select_related('article')
    if verrou:
        qs = qs.select_for_update()
    return list(qs.order_by('id'))


def _articles_session(session: InventaireSession) -> set[str]:
    return set(session.lignes.values_list('article_id', flat=True))


def _ecarts_non_nuls(session: InventaireSession) -> bool:
    return session.lignes.exclude(ecart=None).exclude(ecart=0).exists()


def diagnostiquer_annulation_validation(session: InventaireSession) -> dict:
    """
    Indique si la validation peut être annulée exactement, et avec quel impact.
    Ne modifie rien.
    """
    raisons: list[str] = []

    if session.statut == InventaireSession.STATUT_ANNULE:
        raisons.append('Cet inventaire est déjà annulé.')
        return {'possible': False, 'raisons': raisons, 'impact': None}
    if session.statut != InventaireSession.STATUT_VALIDE:
        raisons.append("Seul un inventaire validé peut faire l'objet d'une annulation de validation.")
        return {'possible': False, 'raisons': raisons, 'impact': None}

    sortie = session.sortie_ajustement
    entree = session.entree_ajustement

    if sortie is None and entree is None and _ecarts_non_nuls(session):
        raisons.append(
            "Les mouvements d'ajustement générés par cet inventaire sont introuvables "
            "(supprimés manuellement ?) : impossible de restaurer exactement la situation."
        )

    quantite_a_restaurer = Decimal('0')
    articles_restaures: set[str] = set()
    if sortie is not None:
        if sortie.entreprise_id != session.entreprise_id:
            raisons.append("La sortie d'ajustement n'appartient pas à cette entreprise.")
        from caisse.models import MouvementCaisse
        from order.models import Commande

        if MouvementCaisse.objects.filter(sortie=sortie).exists():
            raisons.append("La sortie d'ajustement est liée à un mouvement de caisse.")
        if DettesClients.objects.filter(sortie=sortie).exists():
            raisons.append("La sortie d'ajustement est liée à une dette client.")
        if Commande.objects.filter(sortie_livraison=sortie).exists():
            raisons.append("La sortie d'ajustement est liée à une commande livrée.")

        incoherents: list[str] = []
        retour_par_lot: dict[int, Decimal] = defaultdict(Decimal)
        lots: dict[int, LigneEntree] = {}
        for ligne in _lignes_sortie(sortie):
            traces = list(ligne.lots_utilises.all())
            if sum((t.quantite for t in traces), Decimal('0')) != ligne.quantite:
                incoherents.append(_nom_article(ligne.article))
                continue
            for trace in traces:
                retour_par_lot[trace.lot_entree_id] += trace.quantite
                lots[trace.lot_entree_id] = trace.lot_entree
            quantite_a_restaurer += ligne.quantite
            articles_restaures.add(ligne.article_id)
        depassements = sorted({
            _nom_article(lots[lot_id].article)
            for lot_id, retour in retour_par_lot.items()
            if lots[lot_id].quantite_restante + retour > lots[lot_id].quantite
        })
        if incoherents:
            raisons.append(
                "Traçabilité des lots incomplète pour : " + _citer(sorted(incoherents)) + '.'
            )
        if depassements:
            raisons.append(
                "Des lots d'origine ont été modifiés depuis la validation (quantité réduite) : "
                + _citer(depassements) + '.'
            )

    quantite_a_retirer = Decimal('0')
    articles_retires: set[str] = set()
    if entree is not None:
        if entree.entreprise_id != session.entreprise_id:
            raisons.append("L'entrée d'ajustement n'appartient pas à cette entreprise.")
        from order.models import Lot

        if Lot.objects.filter(entree_stock=entree).exists():
            raisons.append("L'entrée d'ajustement est liée à un lot fournisseur.")
        lots_entree = _lots_entree(entree)
        utilises = {
            lot_id
            for lot_id in LigneSortieLot.objects.filter(
                lot_entree__entree=entree,
            ).values_list('lot_entree_id', flat=True)
        } | {
            lot_id
            for lot_id in BeneficeLot.objects.filter(
                lot_entree__entree=entree,
            ).values_list('lot_entree_id', flat=True)
        }
        consommes = sorted({
            _nom_article(lot.article)
            for lot in lots_entree
            if lot.pk in utilises or lot.quantite_restante != lot.quantite
        })
        if consommes:
            raisons.append(
                "Du stock ajouté par cet inventaire a déjà été vendu ou modifié depuis : "
                + _citer(consommes)
                + ". Annulez d'abord ces opérations."
            )
        for lot in lots_entree:
            quantite_a_retirer += lot.quantite
            articles_retires.add(lot.article_id)

    articles = _articles_session(session)
    if session.date_validation is not None:
        posterieurs = (
            InventaireSession.objects.filter(
                entreprise_id=session.entreprise_id,
                statut=InventaireSession.STATUT_VALIDE,
                date_validation__gt=session.date_validation,
                lignes__article_id__in=articles,
            )
            .exclude(pk=session.pk)
            .distinct()
            .order_by('date_validation')
        )
        for autre in posterieurs:
            raisons.append(
                f"L'inventaire #{autre.pk} « {autre.libelle} », validé après celui-ci, porte sur "
                "les mêmes articles : annulez-le d'abord."
            )

    sessions_ouvertes = _sessions_ouvertes_impactees(
        session, articles_restaures | articles_retires,
    )

    return {
        'possible': not raisons,
        'raisons': raisons,
        'impact': {
            'sortie_ajustement_id': sortie.pk if sortie else None,
            'entree_ajustement_id': entree.pk if entree else None,
            'articles_restaures': len(articles_restaures),
            'quantite_restauree': str(quantite_a_restaurer),
            'articles_retires': len(articles_retires),
            'quantite_retiree': str(quantite_a_retirer),
            'inventaires_en_cours_recalcules': [s.pk for s in sessions_ouvertes],
        },
    }


def _sessions_ouvertes_impactees(session: InventaireSession, article_ids: set[str], *, verrou: bool = False):
    """
    Inventaires démarrés après la validation annulée : leur stock théorique a été figé
    sur un stock faussé par cette validation et doit être corrigé du même écart.
    """
    if not article_ids or session.date_validation is None:
        return []
    qs = (
        InventaireSession.objects.filter(
            entreprise_id=session.entreprise_id,
            statut=InventaireSession.STATUT_EN_COURS,
            date_demarrage__gt=session.date_validation,
            lignes__article_id__in=article_ids,
        )
        .exclude(pk=session.pk)
        .distinct()
        .order_by('id')
    )
    if verrou:
        qs = InventaireSession.objects.select_for_update().filter(pk__in=list(qs.values_list('pk', flat=True)))
    return list(qs)


@transaction.atomic
def annuler_validation_session(session: InventaireSession, user, *, motif: str = '') -> InventaireSession:
    """
    Annule les effets d'un inventaire validé et le passe au statut ANNULE.
    Tout ou rien : la moindre erreur annule l'ensemble (transaction).
    """
    session = InventaireSession.objects.select_for_update().get(pk=session.pk)

    sortie = (
        Sortie.objects.select_for_update().filter(pk=session.sortie_ajustement_id).first()
        if session.sortie_ajustement_id else None
    )
    entree = (
        Entree.objects.select_for_update().filter(pk=session.entree_ajustement_id).first()
        if session.entree_ajustement_id else None
    )
    # Tous les verrous sont posés avant la première lecture ordinaire : sous MySQL
    # (REPEATABLE READ) celle-ci fige l'instantané lu ensuite par le diagnostic.
    # Une vente concurrente doit verrouiller le lot avant de le consommer : elle attend.
    lots_entree = _lots_entree(entree, verrou=True) if entree else []
    if sortie is not None:
        lot_ids = sorted(set(
            LigneSortieLot.objects.select_for_update()
            .filter(ligne_sortie__sortie=sortie)
            .values_list('lot_entree_id', flat=True)
        ))
        list(
            LigneEntree.objects.select_for_update()
            .filter(pk__in=lot_ids).order_by('pk').values_list('pk', flat=True)
        )
    lignes_sortie = _lignes_sortie(sortie, verrou=True) if sortie else []

    diagnostic = diagnostiquer_annulation_validation(session)
    if not diagnostic['possible']:
        raise ValidationError({'annulation': diagnostic['raisons']})

    deltas: dict[str, Decimal] = defaultdict(Decimal)
    journal: dict = {
        'date_validation_annulee': session.date_validation.isoformat() if session.date_validation else None,
        'valide_par_id': session.valide_par_id,
        'sortie_ajustement': None,
        'entree_ajustement': None,
        'inventaires_en_cours_recalcules': [],
    }

    if sortie is not None:
        lignes_journal = []
        for ligne in lignes_sortie:
            lots_journal = []
            for trace in ligne.lots_utilises.all():
                lot = LigneEntree.objects.select_for_update().get(pk=trace.lot_entree_id)
                if _q(lot.quantite_restante) + _q(trace.quantite) > _q(lot.quantite):
                    raise ValidationError({'annulation': [
                        f"Le lot #{lot.pk} ({_nom_article(ligne.article)}) a été modifié depuis "
                        "la validation : restauration impossible.",
                    ]})
                lot.quantite_restante = _q(lot.quantite_restante) + _q(trace.quantite)
                lot.save(update_fields=['quantite_restante'])
                lots_journal.append({'lot_id': lot.pk, 'quantite': str(_q(trace.quantite))})
            apply_stock_delta(ligne.article, _q(ligne.quantite))
            deltas[ligne.article_id] += _q(ligne.quantite)
            lignes_journal.append({
                'article_id': ligne.article_id,
                'quantite_restauree': str(_q(ligne.quantite)),
                'lots': lots_journal,
            })
        journal['sortie_ajustement'] = {
            'id': sortie.pk,
            'motif': sortie.motif,
            'date_creation': sortie.date_creation.isoformat(),
            'lignes': lignes_journal,
        }
        # Supprime LigneSortie, LigneSortieLot et BeneficeLot (cascade).
        sortie.delete()

    if entree is not None:
        lots_journal = []
        for lot in lots_entree:
            apply_stock_delta(lot.article, -_q(lot.quantite))
            deltas[lot.article_id] -= _q(lot.quantite)
            lots_journal.append({
                'lot_id': lot.pk,
                'article_id': lot.article_id,
                'quantite_retiree': str(_q(lot.quantite)),
                'prix_unitaire': str(_q(lot.prix_unitaire)),
                'prix_vente': str(_q(lot.prix_vente)),
            })
        journal['entree_ajustement'] = {
            'id': entree.pk,
            'libele': entree.libele,
            'date_op': entree.date_op.isoformat(),
            'lots': lots_journal,
        }
        entree.delete()

    articles_modifies = {aid for aid, delta in deltas.items() if delta != 0}
    for ouverte in _sessions_ouvertes_impactees(session, articles_modifies, verrou=True):
        corrections = []
        for ligne in InventaireLigne.objects.select_for_update().filter(
            session=ouverte, article_id__in=articles_modifies,
        ):
            avant = _q(ligne.stock_theorique)
            ligne.stock_theorique = avant + deltas[ligne.article_id]
            ligne.recalculer_ecart()
            ligne.save(update_fields=['stock_theorique', 'ecart'])
            corrections.append({
                'article_id': ligne.article_id,
                'stock_theorique_avant': str(avant),
                'stock_theorique_apres': str(_q(ligne.stock_theorique)),
            })
        journal['inventaires_en_cours_recalcules'].append({
            'session_id': ouverte.pk,
            'lignes_corrigees': corrections,
        })

    session.statut = InventaireSession.STATUT_ANNULE
    session.validation_annulee = True
    session.annule_par = user if getattr(user, 'is_authenticated', False) else None
    session.date_annulation = timezone.now()
    session.motif_annulation = (motif or '').strip()
    session.journal_annulation = journal
    session.entree_ajustement = None
    session.sortie_ajustement = None
    session.save(update_fields=[
        'statut', 'validation_annulee', 'annule_par', 'date_annulation',
        'motif_annulation', 'journal_annulation', 'entree_ajustement', 'sortie_ajustement',
    ])
    return session
