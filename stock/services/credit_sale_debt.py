"""
Création et réparation des dettes liées aux ventes à crédit (EN_CREDIT).

Règle métier : toute vente à crédit validée doit avoir une DetteClient 1:1 avec la sortie.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils.translation import gettext as _

from stock.models import DetteClient, Devise, LigneSortie, Sortie
from stock.services.currency import build_conversion_snapshot

_LINE_TOTAL = ExpressionWrapper(
    F('quantite') * F('prix_unitaire'),
    output_field=DecimalField(max_digits=14, decimal_places=5),
)


def compute_sortie_line_total(sortie: Sortie) -> Decimal:
    """Montant total d'une sortie (somme quantité × prix unitaire des lignes)."""
    agg = LigneSortie.objects.filter(sortie=sortie).aggregate(total=Sum(_LINE_TOTAL))
    return Decimal(str(agg['total'] or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def resolve_sortie_primary_devise(sortie: Sortie, *, default_devise: Devise | None = None) -> Devise | None:
    """Devise principale d'une sortie : sortie.devise, première ligne, ou devise entreprise."""
    if sortie.devise_id:
        return sortie.devise
    ligne = (
        LigneSortie.objects.filter(sortie=sortie, devise__isnull=False)
        .select_related('devise')
        .order_by('id')
        .first()
    )
    if ligne and ligne.devise_id:
        return ligne.devise
    if default_devise:
        return default_devise
    if sortie.entreprise_id:
        return Devise.objects.filter(entreprise_id=sortie.entreprise_id, est_principal=True).first()
    return None


def create_dette_for_credit_sortie(
    sortie: Sortie,
    *,
    default_devise: Devise | None = None,
    commentaire: str = '',
    raise_if_exists: bool = True,
) -> DetteClient | None:
    """
    Crée la DetteClient pour une sortie EN_CREDIT (idempotent si dette déjà présente).

    Raises:
        ValueError: sortie invalide, client manquant, ou dette déjà existante (si raise_if_exists).
    """
    if sortie.statut != 'EN_CREDIT':
        raise ValueError(_('Seules les sorties EN_CREDIT peuvent générer une dette.'))
    if not sortie.client_id:
        raise ValueError(_('Client obligatoire pour une vente à crédit.'))

    existing = DetteClient.objects.filter(sortie=sortie).first()
    if existing:
        if raise_if_exists:
            raise ValueError(_('Une dette existe déjà pour cette sortie.'))
        return existing

    total_dette = compute_sortie_line_total(sortie)
    if total_dette <= 0:
        raise ValueError(_('Impossible de créer une dette : montant de la vente nul.'))

    devise_dette = resolve_sortie_primary_devise(sortie, default_devise=default_devise)
    if devise_dette is None:
        raise ValueError(_('Devise introuvable pour la vente à crédit.'))

    if not sortie.devise_id:
        Sortie.objects.filter(pk=sortie.pk).update(devise=devise_dette)
        sortie.devise = devise_dette

    snapshot = build_conversion_snapshot(
        entreprise_id=sortie.entreprise_id,
        amount=total_dette,
        devise_source=devise_dette,
    )
    return DetteClient.objects.create(
        sortie=sortie,
        client_id=sortie.client_id,
        montant_total=total_dette,
        devise=devise_dette,
        devise_reference=snapshot['devise_reference'],
        taux_change=snapshot['taux_change'],
        montant_reference=snapshot['montant_reference'],
        entreprise_id=sortie.entreprise_id,
        succursale_id=sortie.succursale_id,
        commentaire=(commentaire or '').strip(),
        statut='EN_COURS',
    )


def find_credit_sorties_without_dette(*, entreprise_id: int | None = None, succursale_id: int | None = None):
    """Sorties EN_CREDIT sans DetteClient correspondante."""
    qs = (
        Sortie.objects.filter(statut='EN_CREDIT', client__isnull=False)
        .exclude(pk__in=DetteClient.objects.values('sortie_id'))
        .select_related('client', 'devise', 'entreprise')
        .prefetch_related('lignes__devise')
        .order_by('date_creation', 'id')
    )
    if entreprise_id is not None:
        qs = qs.filter(entreprise_id=entreprise_id)
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)
    return qs
