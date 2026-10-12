"""
Nature d'une sortie de stock selon son motif.

Seule une sortie qui correspond à une vente au client peut générer un encaissement
(mouvement de caisse ENTREE) ou une dette client. Les autres sorties (produit
défectueux, périmé, volé, endommagé, perte, échantillon, cadeau, prêt, motif libre
non commercial…) diminuent uniquement le stock.

Une sortie est commerciale si son motif est vide (défaut historique de l'API = vente)
ou s'il désigne une vente (« Vente au Client », « Vente du jour », import Excel…).
"""
from __future__ import annotations

import re
import unicodedata

MOTIF_VENTE_CLIENT = 'Vente au Client'

MSG_SORTIE_NON_COMMERCIALE_CREDIT = (
    "Une sortie non commerciale (produit défectueux, périmé, perte, vol…) ne peut pas être "
    "enregistrée à crédit : elle ne génère ni encaissement ni dette client."
)

# Motifs historiques sans le mot « vente » mais créés par des flux de vente.
_MOTIFS_VENTE_EXACTS = frozenset({'', 'import excel'})
_MOTS_VENTE = frozenset({'vente', 'ventes', 'vendu', 'vendue', 'vendus', 'vendues', 'sale', 'sales'})


def _normaliser(motif: str | None) -> str:
    texte = unicodedata.normalize('NFKD', str(motif or '').strip().lower())
    return ''.join(c for c in texte if not unicodedata.combining(c))


def est_sortie_commerciale(motif: str | None) -> bool:
    """True si la sortie est une vente au client (impact caisse / dette autorisé)."""
    norm = _normaliser(motif)
    if norm in _MOTIFS_VENTE_EXACTS:
        return True
    return bool(_MOTS_VENTE.intersection(re.findall(r'[a-z]+', norm)))
