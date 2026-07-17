"""
Service métier : sessions d'inventaire physique et ajustements de stock tracés.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any

from django.db import transaction
from django.db.models import F, OuterRef, Subquery, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from stock.models import (
    Article,
    BeneficeLot,
    Devise,
    Entree,
    InventaireLigne,
    InventaireSession,
    LigneEntree,
    LigneSortie,
    LigneSortieLot,
    Sortie,
    Stock,
)
from stock.services.currency import build_conversion_snapshot
from stock.services.conditionnement_pricing import get_or_create_conditionnement_defaut


def _dec(value, default='0') -> Decimal:
    try:
        return Decimal(str(value if value is not None else default))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _fmt(value: Decimal) -> str:
    return str(value.quantize(Decimal('0.00001'), rounding=ROUND_DOWN))


def _article_qte(stock_row) -> Decimal:
    if stock_row is None:
        return Decimal('0')
    return _dec(stock_row.Qte)


def _dernier_prix_article(article: Article) -> tuple[Decimal, Decimal]:
    """Retourne (prix_achat, prix_vente) du dernier lot ou zéros."""
    last = (
        LigneEntree.objects.filter(article=article)
        .select_related('entree')
        .order_by('-entree__date_op', '-date_entree', '-id')
        .values('prix_unitaire', 'prix_vente')
        .first()
    )
    if not last:
        return Decimal('0'), Decimal('0')
    pu = _dec(last.get('prix_unitaire'))
    pv = _dec(last.get('prix_vente'))
    if pv <= 0:
        pv = pu
    return pu, pv


def _map_derniers_prix_achat(article_ids: list[str]) -> dict[str, Decimal]:
    """Dernier PU d'achat par article (0 si jamais approvisionné)."""
    if not article_ids:
        return {}
    prices: dict[str, Decimal] = {}
    qs = (
        LigneEntree.objects.filter(article_id__in=article_ids)
        .order_by('article_id', '-entree__date_op', '-date_entree', '-id')
        .values_list('article_id', 'prix_unitaire')
    )
    for article_id, prix in qs:
        if article_id in prices:
            continue
        prices[article_id] = _dec(prix)
    return prices


def _articles_queryset(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    perimetre: str,
    type_article_filtre: str = '',
    article_ids: list[str] | None = None,
):
    stock_sq = Stock.objects.filter(article_id=OuterRef('article_id'))
    qs = (
        Article.objects.filter(entreprise_id=entreprise_id)
        .annotate(
            inv_qte=Coalesce(
                F('stock__Qte'),
                Subquery(stock_sq.values('Qte')[:1]),
                Value(Decimal('0.000')),
                output_field=DecimalField(max_digits=12, decimal_places=5),
            ),
        )
        .select_related('unite', 'sous_type_article', 'sous_type_article__type_article')
        .order_by('nom_scientifique', 'article_id')
    )
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)
    if type_article_filtre:
        qs = qs.filter(
            sous_type_article__type_article__libelle__icontains=type_article_filtre,
        )
    if perimetre == InventaireSession.PERIMETRE_EN_STOCK:
        qs = qs.filter(inv_qte__gt=0)
    elif perimetre == InventaireSession.PERIMETRE_PARTIEL:
        ids = [a.strip() for a in (article_ids or []) if a and str(a).strip()]
        if not ids:
            raise ValidationError({'article_ids': 'Liste requise pour le périmètre PARTIEL.'})
        qs = qs.filter(article_id__in=ids)
    return qs


def resume_session(session: InventaireSession) -> dict[str, Any]:
    lignes = list(session.lignes.all())
    total = len(lignes)
    comptees = sum(1 for l in lignes if l.stock_physique is not None)
    avec_ecart = [l for l in lignes if l.ecart is not None and l.ecart != 0]
    capital_logiciel = sum((l.montant_logiciel for l in lignes), Decimal('0'))
    capital_physique = sum(
        (l.montant_physique for l in lignes if l.montant_physique is not None),
        Decimal('0'),
    )
    ecart_financier = capital_physique - capital_logiciel

    ecarts_montant = [
        l.ecart_montant for l in lignes if l.ecart_montant is not None
    ]
    total_ecart_positif = sum(
        (m for m in ecarts_montant if m > 0),
        Decimal('0'),
    )
    total_ecart_negatif = sum(
        (-m for m in ecarts_montant if m < 0),
        Decimal('0'),
    )
    total_ecart_montant = sum(ecarts_montant, Decimal('0'))

    return {
        'total_lignes': total,
        'lignes_comptees': comptees,
        'lignes_non_comptees': total - comptees,
        'ecarts_positifs': sum(1 for l in avec_ecart if l.ecart > 0),
        'ecarts_negatifs': sum(1 for l in avec_ecart if l.ecart < 0),
        'ecarts_nuls': sum(1 for l in lignes if l.ecart is not None and l.ecart == 0),
        'lignes_avec_ecart': len(avec_ecart),
        # Valorisation au dernier PU d'achat figé (photographie).
        'capital_logiciel': _fmt(capital_logiciel),
        'capital_physique': _fmt(capital_physique),
        'ecart_financier': _fmt(ecart_financier),
        # Alias métier pour tableaux de bord / rapports.
        'capital_reel_stock': _fmt(capital_physique),
        'total_montant_logiciel': _fmt(capital_logiciel),
        'total_montant_physique': _fmt(capital_physique),
        # Synthèse des écarts financiers (lignes comptées).
        # total_ecart_negatif = somme des valeurs absolues des manques (toujours ≥ 0).
        'total_ecart_montant': _fmt(total_ecart_montant),
        'total_ecart_positif': _fmt(total_ecart_positif),
        'total_ecart_negatif': _fmt(total_ecart_negatif),
    }


def demarrer_session(
    session: InventaireSession,
    *,
    article_ids: list[str] | None = None,
) -> InventaireSession:
    if session.statut not in (InventaireSession.STATUT_BROUILLON, InventaireSession.STATUT_EN_COURS):
        raise ValidationError('Seul un inventaire brouillon peut être démarré.')
    if session.lignes.exists() and session.statut == InventaireSession.STATUT_EN_COURS:
        raise ValidationError('Cet inventaire est déjà en cours.')

    qs = _articles_queryset(
        entreprise_id=session.entreprise_id,
        succursale_id=session.succursale_id,
        perimetre=session.perimetre,
        type_article_filtre=session.type_article_filtre,
        article_ids=article_ids,
    )
    articles = list(qs)
    if not articles:
        raise ValidationError('Aucun article ne correspond au périmètre choisi.')

    article_ids = [a.article_id for a in articles]
    stock_map = {
        s.article_id: s
        for s in Stock.objects.filter(article_id__in=article_ids)
    }
    prix_map = _map_derniers_prix_achat(article_ids)

    with transaction.atomic():
        session.lignes.all().delete()
        lignes = []
        for article in articles:
            stock_row = stock_map.get(article.article_id)
            qte = _article_qte(stock_row)
            if session.perimetre == InventaireSession.PERIMETRE_EN_STOCK and qte <= 0:
                continue
            lignes.append(
                InventaireLigne(
                    session=session,
                    article=article,
                    stock_theorique=qte,
                    dernier_prix_unitaire=prix_map.get(article.article_id, Decimal('0')),
                )
            )
        if not lignes:
            raise ValidationError('Aucune ligne à inventorier après application des filtres.')
        InventaireLigne.objects.bulk_create(lignes)
        session.statut = InventaireSession.STATUT_EN_COURS
        session.date_demarrage = timezone.now()
        session.save(update_fields=['statut', 'date_demarrage'])

    return session


def mettre_a_jour_ligne(
    ligne: InventaireLigne,
    *,
    stock_physique,
    motif_ligne: str | None = None,
) -> InventaireLigne:
    session = ligne.session
    if session.statut != InventaireSession.STATUT_EN_COURS:
        raise ValidationError('Seul un inventaire en cours accepte la saisie des quantités.')

    qte = _dec(stock_physique)
    if qte < 0:
        raise ValidationError({'stock_physique': 'La quantité physique ne peut pas être négative.'})

    ligne.stock_physique = qte
    if motif_ligne is not None:
        ligne.motif_ligne = motif_ligne
    ligne.recalculer_ecart()
    ligne.save(update_fields=['stock_physique', 'motif_ligne', 'ecart'])
    return ligne


def _consommer_fifo(article: Article, qte: Decimal, devise: Devise | None) -> list[dict]:
    lots = (
        LigneEntree.objects.filter(article=article, quantite_restante__gt=0)
        .order_by('date_entree', 'id')
    )
    restant = qte
    lots_utilises = []
    for lot in lots:
        if restant <= 0:
            break
        preleve = min(lot.quantite_restante, restant)
        lots_utilises.append({'lot': lot, 'quantite': preleve})
        lot.quantite_restante -= preleve
        lot.save(update_fields=['quantite_restante'])
        restant -= preleve

    if restant > 0:
        raise ValidationError(
            f"Stock FIFO insuffisant pour {article.nom_scientifique} "
            f"(manque {_fmt(restant)}). Vérifiez les lots d'entrée."
        )
    return lots_utilises


def _creer_sortie_ajustement(
    session: InventaireSession,
    lignes_neg: list[InventaireLigne],
    devise: Devise | None,
) -> Sortie | None:
    if not lignes_neg:
        return None

    motif = f"Ajustement inventaire #{session.pk} — {session.libelle}"
    sortie = Sortie.objects.create(
        motif=motif,
        statut='PAYEE',
        client=None,
        entreprise_id=session.entreprise_id,
        succursale_id=session.succursale_id,
        devise=devise,
        devise_reference=devise,
    )

    for ligne in lignes_neg:
        qte = abs(_dec(ligne.ecart))
        article = ligne.article
        lots_utilises = _consommer_fifo(article, qte, devise)

        snapshot_ligne = build_conversion_snapshot(
            entreprise_id=sortie.entreprise_id,
            amount=Decimal('0'),
            devise_source=devise,
        )
        ligne_sortie = LigneSortie.objects.create(
            sortie=sortie,
            article=article,
            quantite=qte,
            prix_unitaire=Decimal('0'),
            devise=devise,
            devise_reference=snapshot_ligne['devise_reference'],
            taux_change=snapshot_ligne['taux_change'],
            montant_reference=snapshot_ligne['montant_reference'],
        )

        for lot_data in lots_utilises:
            lot = lot_data['lot']
            qte_lot = lot_data['quantite']
            LigneSortieLot.objects.create(
                ligne_sortie=ligne_sortie,
                lot_entree=lot,
                quantite=qte_lot,
                prix_achat=lot.prix_unitaire,
                prix_vente=lot.prix_vente,
            )
            BeneficeLot.objects.create(
                lot_entree=lot,
                ligne_sortie=ligne_sortie,
                quantite_vendue=qte_lot,
                prix_achat=lot.prix_unitaire,
                prix_vente=Decimal('0'),
                benefice_unitaire=(Decimal('0') - lot.prix_unitaire).quantize(
                    Decimal('0.00001'), rounding=ROUND_DOWN,
                ),
                benefice_total=(Decimal('0') - lot.prix_unitaire * qte_lot).quantize(
                    Decimal('0.00001'), rounding=ROUND_DOWN,
                ),
            )

        stock_obj, _ = Stock.objects.get_or_create(
            article=article,
            defaults={'Qte': 0, 'seuilAlert': 0},
        )
        stock_obj.Qte -= qte
        stock_obj.save(update_fields=['Qte'])

    return sortie


def _creer_entree_ajustement(
    session: InventaireSession,
    lignes_pos: list[InventaireLigne],
    devise: Devise | None,
) -> Entree | None:
    if not lignes_pos:
        return None

    libelle = f"Ajustement inventaire #{session.pk} — {session.libelle}"
    entree = Entree.objects.create(
        libele=libelle,
        description=session.commentaire or '',
        entreprise_id=session.entreprise_id,
        succursale_id=session.succursale_id,
    )

    for ligne in lignes_pos:
        qte = _dec(ligne.ecart)
        article = ligne.article
        # Préférer le PU figé de l'inventaire (photographie) pour l'ajustement +.
        pu_fige = _dec(ligne.dernier_prix_unitaire)
        pu_actuel, pv = _dernier_prix_article(article)
        pu = pu_fige if pu_fige > 0 else pu_actuel
        if pv <= 0:
            pv = Decimal('0.00001') if pu <= 0 else pu

        stock_obj, created = Stock.objects.get_or_create(
            article=article,
            defaults={'Qte': 0, 'seuilAlert': 0},
        )
        seuil = stock_obj.seuilAlert if not created else Decimal('0')

        montant_ligne = (pu * qte).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        snapshot_ligne = build_conversion_snapshot(
            entreprise_id=entree.entreprise_id,
            amount=montant_ligne,
            devise_source=devise,
        )
        conditionnement_defaut = get_or_create_conditionnement_defaut(article)
        LigneEntree.objects.create(
            entree=entree,
            article=article,
            conditionnement=conditionnement_defaut,
            quantite_saisie=qte,
            quantite_base=qte,
            quantite=qte,
            quantite_restante=qte,
            prix_achat_conditionnement=pu,
            prix_vente_conditionnement=pv,
            prix_achat_unitaire_base=pu,
            prix_vente_unitaire_base=pv,
            prix_unitaire=pu,
            prix_vente=pv,
            devise=devise,
            devise_reference=snapshot_ligne['devise_reference'],
            taux_change=snapshot_ligne['taux_change'],
            montant_reference=snapshot_ligne['montant_reference'],
            seuil_alerte=seuil,
        )
        stock_obj.Qte += qte
        stock_obj.save(update_fields=['Qte'])

    return entree


def valider_session(session: InventaireSession, user) -> InventaireSession:
    if session.statut != InventaireSession.STATUT_EN_COURS:
        raise ValidationError('Seul un inventaire en cours peut être validé.')

    lignes = list(
        session.lignes.select_related('article').order_by('article__nom_scientifique')
    )
    if not lignes:
        raise ValidationError('Aucune ligne dans cette session.')

    non_comptees = [l for l in lignes if l.stock_physique is None]
    if non_comptees:
        raise ValidationError(
            f"{len(non_comptees)} article(s) n'ont pas encore de stock physique saisi."
        )

    devise = Devise.objects.filter(
        entreprise_id=session.entreprise_id,
        est_principal=True,
    ).first()

    lignes_pos = [l for l in lignes if l.ecart and l.ecart > 0]
    lignes_neg = [l for l in lignes if l.ecart and l.ecart < 0]

    with transaction.atomic():
        entree = _creer_entree_ajustement(session, lignes_pos, devise)
        sortie = _creer_sortie_ajustement(session, lignes_neg, devise)

        session.entree_ajustement = entree
        session.sortie_ajustement = sortie
        session.statut = InventaireSession.STATUT_VALIDE
        session.valide_par = user
        session.date_validation = timezone.now()
        session.save(update_fields=[
            'entree_ajustement', 'sortie_ajustement', 'statut',
            'valide_par', 'date_validation',
        ])

    return session


def annuler_session(session: InventaireSession) -> InventaireSession:
    if session.statut == InventaireSession.STATUT_VALIDE:
        raise ValidationError('Un inventaire validé ne peut plus être annulé.')
    session.statut = InventaireSession.STATUT_ANNULE
    session.save(update_fields=['statut'])
    return session
