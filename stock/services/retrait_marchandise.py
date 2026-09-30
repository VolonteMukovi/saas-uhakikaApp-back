"""Personne venue retirer une vente à crédit (optionnel)."""
from __future__ import annotations

from rest_framework import serializers

RETIRE_PAR_MAX = 150


def nettoyer_retire_par(raw, statut: str) -> str:
    """
    Nom affiché sur la facture. Vide si absent.
    Refusé hors vente à crédit.
    """
    nom = ' '.join(str(raw or '').split())
    if len(nom) > RETIRE_PAR_MAX:
        raise serializers.ValidationError({
            'retire_par': (
                f'Le nom de la personne qui retire ne peut pas dépasser {RETIRE_PAR_MAX} caractères.'
            ),
        })
    if nom and str(statut or '').upper() != 'EN_CREDIT':
        raise serializers.ValidationError({
            'retire_par': (
                "La personne qui retire la marchandise ne s'enregistre que pour une vente à crédit."
            ),
        })
    if str(statut or '').upper() != 'EN_CREDIT':
        return ''
    return nom
