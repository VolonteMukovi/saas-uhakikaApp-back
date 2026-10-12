"""
Annulation d'une entrée (approvisionnement) ou d'une sortie (vente, sortie non commerciale).

L'annulation remet le stock et la caisse exactement dans l'état antérieur au mouvement :

- sortie : chaque lot FIFO consommé récupère sa quantité (même lot, même prix), le stock
  global est réaugmenté, les traces de lots et bénéfices sont retirées (rollback_sortie_ligne),
  la dette éventuelle (sans paiement) disparaît avec la sortie ;
- entrée : les lots créés sont retirés et le stock global diminué d'autant, à condition
  qu'aucune unité n'ait été consommée depuis ;
- caisse : chaque mouvement réellement enregistré pour la pièce (montant > 0) reçoit une
  contre-écriture de même montant, même caisse, même devise et même catégorie, en sens
  inverse. Les mouvements d'origine ne sont ni supprimés ni modifiés. Sans mouvement
  d'origine (sortie non commerciale, vente à crédit, approvisionnement non payé),
  aucune écriture n'est créée.

La pièce annulée est ensuite supprimée (comme l'annulation d'inventaire validé), son détail
exact étant conservé dans AnnulationMouvement. Tout se fait dans une transaction :
la moindre erreur n'en laisse aucune trace.

L'annulation est refusée, avec une explication, dès qu'elle compromettrait l'intégrité des
données : stock de l'approvisionnement déjà vendu, paiements enregistrés sur la dette,
pièce générée par un autre module (inventaire, commande, lot fournisseur), inventaire validé
depuis sur les mêmes articles, caisse fermée ou solde insuffisant…
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from caisse.models import MouvementCaisse
from caisse.services.caisse_defaut import CaisseError, caisse_necessite_session
from caisse.services.errors import validation_error_message
from caisse.services.session_caisse import (
    SessionCaisseError,
    get_session_ouverte_for_caisse,
    solde_session_courant,
)
from stock.models import (
    AnnulationMouvement,
    Entree,
    InventaireSession,
    LigneEntree,
    LigneSortie,
    LigneSortieLot,
    Sortie,
)
from stock.services.sortie_motif import est_sortie_commerciale
from stock.services.stock_adjustment import (
    apply_stock_delta,
    quantize_qty,
    rollback_sortie_ligne,
)

MAX_ARTICLES_CITES = 10
CODE_IMPOSSIBLE = 'annulation_impossible'


class MouvementDejaAnnule(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'mouvement_deja_annule'
    default_detail = 'Ce mouvement a déjà été annulé.'


def _nom_article(article) -> str:
    return article.nom_commercial or article.nom_scientifique or article.article_id


def _citer(noms) -> str:
    noms = sorted(set(noms))
    extrait = ', '.join(noms[:MAX_ARTICLES_CITES])
    if len(noms) > MAX_ARTICLES_CITES:
        extrait += f' … (+{len(noms) - MAX_ARTICLES_CITES})'
    return extrait


def _qte(value) -> str:
    """Quantité lisible dans un message (3 et non 3.00000)."""
    texte = f'{quantize_qty(value).normalize():f}'
    return texte.rstrip('0').rstrip('.') if '.' in texte else texte


def _nom_utilisateur(user) -> str:
    if user is None:
        return ''
    full = (user.get_full_name() or '').strip() if hasattr(user, 'get_full_name') else ''
    return full or getattr(user, 'username', '') or getattr(user, 'email', '') or ''


def libelle_sortie(sortie: Sortie) -> str:
    prefixe = 'Vente' if est_sortie_commerciale(sortie.motif) else 'Sortie'
    return f'{prefixe} #{sortie.pk}'


def libelle_entree(entree: Entree) -> str:
    return f'Approvisionnement #{entree.pk}'


def verifier_non_annule(entreprise_id: int, type_mouvement: str, reference_id) -> None:
    """Lève 409 si ce mouvement a déjà été annulé (idempotence)."""
    try:
        reference_id = int(reference_id)
    except (TypeError, ValueError):
        return
    deja = AnnulationMouvement.objects.filter(
        entreprise_id=entreprise_id,
        type_mouvement=type_mouvement,
        reference_id=reference_id,
    ).first()
    if deja is not None:
        par = f' par {deja.annule_par_nom}' if deja.annule_par_nom else ''
        quand = timezone.localtime(deja.date_annulation)
        raise MouvementDejaAnnule(
            f"L'annulation de {deja.reference_libelle or 'ce mouvement'} a déjà été effectuée le "
            f"{quand:%d/%m/%Y à %H:%M}{par}. Aucune nouvelle modification n'a été effectuée."
        )


# ---------------------------------------------------------------------------
# Caisse
# ---------------------------------------------------------------------------

def _mouvements_caisse_origine(*, sortie: Sortie | None = None, entree: Entree | None = None) -> list[MouvementCaisse]:
    qs = MouvementCaisse.objects.select_related('devise', 'type_caisse')
    qs = qs.filter(sortie=sortie) if sortie is not None else qs.filter(entree=entree)
    return list(qs.filter(montant__gt=0).order_by('id'))


def _impact_caisse(mouvements: list[MouvementCaisse]) -> tuple[list[dict], list[str]]:
    """Contre-écritures à passer et raisons de refus éventuelles (caisse fermée, solde…)."""
    impacts: list[dict] = []
    raisons: list[str] = []
    besoin_par_session: dict[int, Decimal] = defaultdict(Decimal)
    for mv in mouvements:
        sens_inverse = 'SORTIE' if mv.type == 'ENTREE' else 'ENTREE'
        tc = mv.type_caisse
        caisse_nom = tc.libelle_affiche if tc else ''
        impacts.append({
            'mouvement_origine_id': mv.pk,
            'reference_piece': mv.reference_piece,
            'type_origine': mv.type,
            'type_annulation': sens_inverse,
            'montant': str(mv.montant),
            'devise': mv.devise.sigle if mv.devise else '',
            'caisse_id': mv.type_caisse_id,
            'caisse': caisse_nom,
            'categorie': mv.categorie,
        })
        if tc is None:
            continue
        if not tc.is_active:
            raisons.append(f"La caisse « {caisse_nom} » est désactivée : impossible d'y passer la contre-écriture.")
            continue
        if tc.devise_id and mv.devise_id and tc.devise_id != mv.devise_id:
            raisons.append(
                f"La devise de la caisse « {caisse_nom} » a changé depuis l'opération : "
                "la contre-écriture ne peut pas être passée à l'identique."
            )
            continue
        try:
            session = get_session_ouverte_for_caisse(tc, mv.succursale_id, mv.devise_id)
        except SessionCaisseError as exc:
            raisons.append(f"Caisse « {caisse_nom} » : {validation_error_message(exc)}")
            continue
        if sens_inverse == 'SORTIE' and session is not None and caisse_necessite_session(tc):
            besoin_par_session[session.pk] += mv.montant
            solde = solde_session_courant(session)
            if besoin_par_session[session.pk] > solde:
                raisons.append(
                    f"Solde insuffisant dans la caisse « {caisse_nom} » pour reprendre "
                    f"{mv.montant} {impacts[-1]['devise']} (solde de la session ouverte : {solde})."
                )
    return impacts, raisons


def _passer_contre_ecritures(mouvements: list[MouvementCaisse], *, annulation: AnnulationMouvement, user) -> list[dict]:
    from caisse.services.caisse import creer_mouvement_caisse

    resultats = []
    for mv in mouvements:
        sens_inverse = 'SORTIE' if mv.type == 'ENTREE' else 'ENTREE'
        try:
            contre = creer_mouvement_caisse(
                montant=mv.montant,
                devise=mv.devise,
                type_mouvement=sens_inverse,
                entreprise_id=mv.entreprise_id or annulation.entreprise_id,
                succursale_id=mv.succursale_id,
                content_object=annulation,
                utilisateur=user,
                reference_piece=f'ANN-{mv.reference_piece or mv.pk}'[:100],
                motif=(
                    f'Annulation {annulation.reference_libelle} '
                    f'(contre-écriture du mouvement de caisse #{mv.pk})'
                ),
                moyen=mv.moyen,
                type_caisse=mv.type_caisse,
                categorie=mv.categorie or 'AUTRE',
                skip_session_check=mv.type_caisse_id is None,
                devise_reference=mv.devise_reference,
                taux_change=mv.taux_change,
                montant_reference=mv.montant_reference,
            )
        except (CaisseError, SessionCaisseError) as exc:
            raise ValidationError({'detail': validation_error_message(exc), 'code': CODE_IMPOSSIBLE}) from exc
        resultats.append({
            'mouvement_origine_id': mv.pk,
            'mouvement_annulation_id': contre.pk,
            'type_annulation': sens_inverse,
            'montant': str(contre.montant),
            'devise': contre.devise.sigle if contre.devise else '',
            'caisse_id': contre.type_caisse_id,
        })
    return resultats


# ---------------------------------------------------------------------------
# Contrôles communs
# ---------------------------------------------------------------------------

def _inventaires_posterieurs(entreprise_id: int, date_mouvement, article_ids: set[str]) -> list[str]:
    if not article_ids or date_mouvement is None:
        return []
    qs = (
        InventaireSession.objects.filter(
            entreprise_id=entreprise_id,
            statut=InventaireSession.STATUT_VALIDE,
            date_validation__gt=date_mouvement,
            lignes__article_id__in=article_ids,
        )
        .distinct()
        .order_by('date_validation')
    )
    return [
        f"L'inventaire #{inv.pk} « {inv.libelle} », validé après ce mouvement, a fixé le stock "
        "réel des mêmes articles : l'annulation fausserait ce comptage."
        for inv in qs
    ]


def _lever_si_impossible(diagnostic: dict) -> None:
    if not diagnostic['possible']:
        raisons = diagnostic['raisons']
        raise ValidationError({
            'detail': 'Annulation impossible : ' + ' '.join(raisons),
            'code': CODE_IMPOSSIBLE,
        })


# ---------------------------------------------------------------------------
# Sorties
# ---------------------------------------------------------------------------

def _lignes_sortie(sortie: Sortie) -> list[LigneSortie]:
    return list(
        LigneSortie.objects.filter(sortie=sortie)
        .select_related('article', 'devise', 'conditionnement')
        .prefetch_related('lots_utilises__lot_entree')
        .order_by('id')
    )


def diagnostiquer_annulation_sortie(sortie: Sortie) -> dict:
    """Indique si la sortie peut être annulée et avec quel impact. Ne modifie rien."""
    from order.models import Commande
    from stock.models import DettesClients

    raisons: list[str] = []
    commerciale = est_sortie_commerciale(sortie.motif)

    commande = Commande.objects.filter(sortie_livraison=sortie).first()
    if commande is not None:
        raisons.append(
            f"Cette sortie a été générée par la livraison de la commande "
            f"{(commande.reference or '').strip() or '#' + str(commande.pk)} : gérez-la depuis le module Commandes."
        )
    if InventaireSession.objects.filter(sortie_ajustement=sortie).exists():
        raisons.append(
            "Cette sortie est un ajustement d'inventaire : utilisez l'annulation de l'inventaire."
        )

    dette = DettesClients.objects.filter(sortie=sortie).first()
    if dette is not None and dette.paiements.exists():
        raisons.append(
            f"Des paiements ({dette.paye}) ont déjà été enregistrés sur la dette de cette vente : "
            "l'annulation effacerait des encaissements réels."
        )

    lignes = _lignes_sortie(sortie)
    impact_stock = []
    incoherents, depassements = [], []
    retour_par_lot: dict[int, Decimal] = defaultdict(Decimal)
    lots: dict[int, LigneEntree] = {}
    for ligne in lignes:
        traces = list(ligne.lots_utilises.all())
        if quantize_qty(sum((t.quantite for t in traces), Decimal('0'))) != quantize_qty(ligne.quantite):
            incoherents.append(_nom_article(ligne.article))
        for trace in traces:
            retour_par_lot[trace.lot_entree_id] += trace.quantite
            lots[trace.lot_entree_id] = trace.lot_entree
        impact_stock.append({
            'article_id': ligne.article_id,
            'article': _nom_article(ligne.article),
            'quantite': str(quantize_qty(ligne.quantite)),
            'sens': 'RESTAURATION',
        })
    for lot_id, retour in retour_par_lot.items():
        lot = lots[lot_id]
        if quantize_qty(lot.quantite_restante) + quantize_qty(retour) > quantize_qty(lot.quantite):
            depassements.append(_nom_article(lot.article))
    if incoherents:
        raisons.append(
            'Traçabilité des lots incomplète pour : ' + _citer(incoherents)
            + ' ; la restauration exacte du stock est impossible.'
        )
    if depassements:
        raisons.append(
            "Les lots d'origine ont été modifiés depuis la sortie (quantité réduite) : "
            + _citer(depassements) + '.'
        )
    raisons += _inventaires_posterieurs(
        sortie.entreprise_id, sortie.date_creation, {ligne.article_id for ligne in lignes},
    )

    mouvements = _mouvements_caisse_origine(sortie=sortie)
    impact_caisse, raisons_caisse = _impact_caisse(mouvements)
    raisons += raisons_caisse

    return {
        'possible': not raisons,
        'raisons': raisons,
        'type_mouvement': AnnulationMouvement.TYPE_SORTIE,
        'nature': (
            AnnulationMouvement.NATURE_VENTE if commerciale
            else AnnulationMouvement.NATURE_SORTIE_NON_COMMERCIALE
        ),
        'reference_id': sortie.pk,
        'reference': libelle_sortie(sortie),
        'motif': sortie.motif,
        'statut': sortie.statut,
        'date_mouvement': sortie.date_creation.isoformat() if sortie.date_creation else None,
        'impact_stock': impact_stock,
        'impact_caisse': impact_caisse,
        'dette_supprimee': dette is not None,
    }


@transaction.atomic
def annuler_sortie(sortie: Sortie, user, *, motif: str = '') -> AnnulationMouvement:
    """Annule une sortie : tout ou rien (transaction)."""
    entreprise_id, sortie_id = sortie.entreprise_id, sortie.pk
    # Tous les verrous sont posés avant la première lecture ordinaire : sous MySQL
    # (REPEATABLE READ) celle-ci fige l'instantané lu ensuite par le diagnostic.
    # Une vente concurrente doit verrouiller le lot avant de le consommer : elle attend.
    sortie = Sortie.objects.select_for_update().filter(pk=sortie_id).first()
    if sortie is not None:
        lot_ids = sorted(set(
            LigneSortieLot.objects.select_for_update()
            .filter(ligne_sortie__sortie=sortie).values_list('lot_entree_id', flat=True)
        ))
        list(LigneEntree.objects.select_for_update().filter(pk__in=lot_ids).order_by('pk').values_list('pk', flat=True))
        list(MouvementCaisse.objects.select_for_update().filter(sortie=sortie).values_list('pk', flat=True))
    verifier_non_annule(entreprise_id, AnnulationMouvement.TYPE_SORTIE, sortie_id)
    if sortie is None:
        raise MouvementDejaAnnule()

    diagnostic = diagnostiquer_annulation_sortie(sortie)
    _lever_si_impossible(diagnostic)

    lignes = _lignes_sortie(sortie)
    journal_lignes = [
        {
            'ligne_id': ligne.pk,
            'article_id': ligne.article_id,
            'article': _nom_article(ligne.article),
            'quantite': str(quantize_qty(ligne.quantite)),
            'prix_unitaire': str(ligne.prix_unitaire),
            'montant_total': str(ligne.get_montant_total()),
            'devise': ligne.devise.sigle if ligne.devise else '',
            'lots': [
                {'lot_id': t.lot_entree_id, 'quantite': str(quantize_qty(t.quantite))}
                for t in ligne.lots_utilises.all()
            ],
        }
        for ligne in lignes
    ]
    annulation = _creer_journal(
        sortie.entreprise_id, sortie.succursale_id, AnnulationMouvement.TYPE_SORTIE, diagnostic, user, motif,
        date_mouvement=sortie.date_creation,
        journal={
            'motif': sortie.motif,
            'statut': sortie.statut,
            'client_id': sortie.client_id,
            'retire_par': sortie.retire_par,
            'lignes': journal_lignes,
        },
    )

    # Stock : chaque lot récupère exactement ce qu'il avait fourni.
    for ligne in lignes:
        rollback_sortie_ligne(ligne)

    # Caisse : contre-écritures des seuls encaissements réellement enregistrés.
    annulation.impact_caisse = _passer_contre_ecritures(
        _mouvements_caisse_origine(sortie=sortie), annulation=annulation, user=user,
    )
    annulation.save(update_fields=['impact_caisse'])

    # Supprime la dette éventuelle (sans paiement, vérifié) par cascade.
    sortie.delete()
    return annulation


# ---------------------------------------------------------------------------
# Entrées
# ---------------------------------------------------------------------------

def diagnostiquer_annulation_entree(entree: Entree) -> dict:
    """Indique si l'approvisionnement peut être annulé et avec quel impact. Ne modifie rien."""
    from order.models import Lot
    from stock.models import Stock

    raisons: list[str] = []
    if InventaireSession.objects.filter(entree_ajustement=entree).exists():
        raisons.append(
            "Cette entrée est un ajustement d'inventaire : utilisez l'annulation de l'inventaire."
        )
    if Lot.objects.filter(entree_stock=entree).exists():
        raisons.append(
            "Cette entrée a été générée par la clôture d'un lot fournisseur : gérez-la depuis ce module."
        )

    lots = list(LigneEntree.objects.filter(entree=entree).select_related('article').order_by('id'))
    lots_utilises = set(
        LigneSortieLot.objects.filter(lot_entree__entree=entree).values_list('lot_entree_id', flat=True)
    )
    consommes = []
    impact_stock = []
    retrait_par_article: dict[str, Decimal] = defaultdict(Decimal)
    articles = {}
    for lot in lots:
        vendue = quantize_qty(lot.quantite) - quantize_qty(lot.quantite_restante)
        if lot.pk in lots_utilises or vendue != 0:
            consommes.append(f'{_nom_article(lot.article)} ({_qte(vendue)} unité(s) déjà sorties)')
        retrait_par_article[lot.article_id] += quantize_qty(lot.quantite)
        articles[lot.article_id] = lot.article
        impact_stock.append({
            'article_id': lot.article_id,
            'article': _nom_article(lot.article),
            'quantite': str(quantize_qty(lot.quantite)),
            'sens': 'RETRAIT',
        })
    if consommes:
        raisons.append(
            "Une partie du stock de cet approvisionnement a déjà été vendue ou sortie : "
            + _citer(consommes) + ". Annulez d'abord ces sorties."
        )
    stocks = {
        s.article_id: quantize_qty(s.Qte)
        for s in Stock.objects.filter(article_id__in=list(retrait_par_article))
    }
    negatifs = [
        _nom_article(articles[aid])
        for aid, qte in retrait_par_article.items()
        if stocks.get(aid, Decimal('0')) - qte < 0
    ]
    if negatifs and not consommes:
        raisons.append(
            'Le stock actuel est inférieur à la quantité approvisionnée pour : '
            + _citer(negatifs) + ' ; le retrait rendrait le stock négatif.'
        )
    raisons += _inventaires_posterieurs(entree.entreprise_id, entree.date_op, set(retrait_par_article))

    mouvements = _mouvements_caisse_origine(entree=entree)
    impact_caisse, raisons_caisse = _impact_caisse(mouvements)
    raisons += raisons_caisse

    return {
        'possible': not raisons,
        'raisons': raisons,
        'type_mouvement': AnnulationMouvement.TYPE_ENTREE,
        'nature': AnnulationMouvement.NATURE_APPROVISIONNEMENT,
        'reference_id': entree.pk,
        'reference': libelle_entree(entree),
        'motif': entree.libele,
        'statut': None,
        'date_mouvement': entree.date_op.isoformat() if entree.date_op else None,
        'impact_stock': impact_stock,
        'impact_caisse': impact_caisse,
        'dette_supprimee': False,
    }


@transaction.atomic
def annuler_entree(entree: Entree, user, *, motif: str = '') -> AnnulationMouvement:
    """Annule un approvisionnement : tout ou rien (transaction)."""
    entreprise_id, entree_id = entree.entreprise_id, entree.pk
    entree = Entree.objects.select_for_update().filter(pk=entree_id).first()
    lots = []
    if entree is not None:
        lots = list(
            LigneEntree.objects.select_for_update().filter(entree=entree).select_related('article').order_by('pk')
        )
        list(MouvementCaisse.objects.select_for_update().filter(entree=entree).values_list('pk', flat=True))
    verifier_non_annule(entreprise_id, AnnulationMouvement.TYPE_ENTREE, entree_id)
    if entree is None:
        raise MouvementDejaAnnule()

    diagnostic = diagnostiquer_annulation_entree(entree)
    _lever_si_impossible(diagnostic)

    annulation = _creer_journal(
        entree.entreprise_id, entree.succursale_id, AnnulationMouvement.TYPE_ENTREE, diagnostic, user, motif,
        date_mouvement=entree.date_op,
        journal={
            'libele': entree.libele,
            'description': entree.description,
            'source_requisition_id': entree.source_requisition_id,
            'lots': [
                {
                    'lot_id': lot.pk,
                    'article_id': lot.article_id,
                    'article': _nom_article(lot.article),
                    'quantite': str(quantize_qty(lot.quantite)),
                    'prix_unitaire': str(lot.prix_unitaire),
                    'prix_vente': str(lot.prix_vente),
                    'devise_id': lot.devise_id,
                    'date_expiration': lot.date_expiration.isoformat() if lot.date_expiration else None,
                }
                for lot in lots
            ],
        },
    )

    for lot in lots:
        apply_stock_delta(lot.article, -quantize_qty(lot.quantite))

    annulation.impact_caisse = _passer_contre_ecritures(
        _mouvements_caisse_origine(entree=entree), annulation=annulation, user=user,
    )
    annulation.save(update_fields=['impact_caisse'])

    requisition = entree.source_requisition
    # Supprime les lots et leurs prix par conditionnement (cascade).
    entree.delete()
    if requisition is not None:
        _rouvrir_requisition(requisition, entree_id=annulation.reference_id, user=user)
    return annulation


def _rouvrir_requisition(requisition, *, entree_id: int, user) -> None:
    """La réquisition redevient transformable si plus aucun approvisionnement n'en découle."""
    from stock.models import Requisition
    from stock.services import requisition as requisition_service

    if not requisition.approvisionnements.exists():
        requisition.transformation_status = Requisition.TRANSFO_NON
        requisition.transformed_at = None
        requisition.save(update_fields=['transformation_status', 'transformed_at', 'date_modification'])
    requisition_service.log_historique(
        requisition,
        action='ANNULATION_APPROVISIONNEMENT',
        utilisateur=user,
        detail=f'Approvisionnement #{entree_id} annulé',
        metadata={'entree_id': entree_id},
    )


def _creer_journal(
    entreprise_id, succursale_id, type_mouvement, diagnostic, user, motif, *, date_mouvement, journal,
) -> AnnulationMouvement:
    try:
        with transaction.atomic():
            return AnnulationMouvement.objects.create(
                entreprise_id=entreprise_id,
                succursale_id=succursale_id,
                type_mouvement=type_mouvement,
                nature=diagnostic['nature'],
                reference_id=diagnostic['reference_id'],
                reference_libelle=diagnostic['reference'],
                motif_origine=(diagnostic['motif'] or '')[:255],
                date_mouvement=date_mouvement,
                motif_annulation=(motif or '').strip(),
                annule_par=user if getattr(user, 'is_authenticated', False) else None,
                annule_par_nom=_nom_utilisateur(user),
                impact_stock=diagnostic['impact_stock'],
                impact_caisse=diagnostic['impact_caisse'],
                journal=journal,
            )
    except IntegrityError as exc:
        raise MouvementDejaAnnule() from exc
