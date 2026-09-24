"""
Statut métier d'une DetteClient.

Règle :
- solde restant <= tolérance d'arrondi → PAYEE (même avant l'échéance)
- sinon échéance dépassée → RETARD
- sinon → EN_COURS

Tolérance : 1 unité sur 5 décimales (0.00001) pour absorber
les résidus type total=15.96000 / payé=15.95999 → solde=0.00001.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from django.utils import timezone

from stock.models import DetteClient

_MONEY = Decimal('0.00001')
# Solde résiduel considéré comme nul (artefact d'arrondi / conversion)
_SOLDE_EPS = Decimal('0.00001')


def solde_restant_q(dette: DetteClient) -> Decimal:
    total = Decimal(str(dette.montant_total or 0))
    paye = Decimal(str(dette.montant_paye or 0))
    return (total - paye).quantize(_MONEY, rounding=ROUND_DOWN)


def solde_effectif(dette: DetteClient, *, solde: Decimal | None = None) -> Decimal:
    """Solde après absorption du micro-résidu d'arrondi."""
    if solde is None:
        solde = solde_restant_q(dette)
    else:
        solde = Decimal(str(solde)).quantize(_MONEY, rounding=ROUND_DOWN)
    if solde <= _SOLDE_EPS:
        return Decimal('0.00000')
    return solde


def compute_statut_dette(dette: DetteClient, *, solde: Decimal | None = None) -> str:
    """Calcule le statut attendu sans écrire en base."""
    solde_eff = solde_effectif(dette, solde=solde)

    if solde_eff <= 0:
        return 'PAYEE'

    today = timezone.now().date()
    if dette.date_echeance and dette.date_echeance < today:
        return 'RETARD'
    return 'EN_COURS'


def appliquer_statut_dette(dette_id: int) -> str | None:
    """Recalcule et persiste le statut. Retourne le nouveau statut ou None si introuvable."""
    dette = DetteClient.objects.filter(pk=dette_id).first()
    if not dette:
        return None
    statut = compute_statut_dette(dette)
    if dette.statut != statut:
        DetteClient.objects.filter(pk=dette_id).update(statut=statut)
    return statut


def sync_statuts_dettes(*, entreprise_id: int | None = None, succursale_id: int | None = None) -> dict:
    """
    Aligne le statut de toutes les dettes (corrige EN_COURS soldées, etc.).
    Retourne des compteurs.
    """
    qs = DetteClient.objects.all().select_related('client')
    if entreprise_id is not None:
        qs = qs.filter(entreprise_id=entreprise_id)
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)

    counts = {'scannees': 0, 'mises_a_jour': 0, 'payees': 0, 'en_cours': 0, 'retard': 0}
    for dette in qs.iterator(chunk_size=200):
        counts['scannees'] += 1
        nouveau = compute_statut_dette(dette)
        if nouveau == 'PAYEE':
            counts['payees'] += 1
        elif nouveau == 'EN_COURS':
            counts['en_cours'] += 1
        else:
            counts['retard'] += 1
        if dette.statut != nouveau:
            DetteClient.objects.filter(pk=dette.pk).update(statut=nouveau)
            counts['mises_a_jour'] += 1
    return counts


def fmt_money(value: Decimal | None) -> str:
    if value is None:
        return '0.00000'
    return str(Decimal(str(value)).quantize(_MONEY, rounding=ROUND_HALF_UP))
