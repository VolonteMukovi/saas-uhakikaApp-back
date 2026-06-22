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
        .order_by('-date_entree', '-id')
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
    lignes = session.lignes.all()
    total = lignes.count()
    comptees = lignes.filter(stock_physique__isnull=False).count()
    avec_ecart = lignes.filter(ecart__isnull=False).exclude(ecart=0)
    return {
        'total_lignes': total,
        'lignes_comptees': comptees,
        'lignes_non_comptees': total - comptees,
        'ecarts_positifs': avec_ecart.filter(ecart__gt=0).count(),
        'ecarts_negatifs': avec_ecart.filter(ecart__lt=0).count(),
        'ecarts_nuls': lignes.filter(ecart=0).count(),
        'lignes_avec_ecart': avec_ecart.count(),
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

    stock_map = {
        s.article_id: s
        for s in Stock.objects.filter(article_id__in=[a.article_id for a in articles])
    }

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
    )

    for ligne in lignes_neg:
        qte = abs(_dec(ligne.ecart))
        article = ligne.article
        lots_utilises = _consommer_fifo(article, qte, devise)

        ligne_sortie = LigneSortie.objects.create(
            sortie=sortie,
            article=article,
            quantite=qte,
            prix_unitaire=Decimal('0'),
            devise=devise,
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
        pu, pv = _dernier_prix_article(article)
        if pv <= 0:
            pv = Decimal('0.00001')

        stock_obj, created = Stock.objects.get_or_create(
            article=article,
            defaults={'Qte': 0, 'seuilAlert': 0},
        )
        seuil = stock_obj.seuilAlert if not created else Decimal('0')

        LigneEntree.objects.create(
            entree=entree,
            article=article,
            quantite=qte,
            quantite_restante=qte,
            prix_unitaire=pu,
            prix_vente=pv,
            devise=devise,
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
