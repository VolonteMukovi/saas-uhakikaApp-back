"""Journal des suppressions de ventes (GET /api/logs-suppressions/)."""
from __future__ import annotations

from typing import Iterable

from stock.models import LigneSortie, LogSuppression, Sortie


def _nom_utilisateur(user) -> str:
    if user is None or not getattr(user, 'is_authenticated', False):
        return ''
    full = (user.get_full_name() or '').strip()
    return full or user.get_username()


def _nom_article(article) -> str:
    if article is None:
        return ''
    return (article.nom_commercial or article.nom_scientifique or str(article.pk)).strip()


def journaliser_lignes_supprimees(
    sortie: Sortie,
    lignes: Iterable[LigneSortie],
    user,
    *,
    motif: str,
    entreprise_id: int | None = None,
) -> list[LogSuppression]:
    """
    Enregistre une entrée par ligne retirée. À appeler **avant** la suppression
    (dans la même transaction) pour figer article, quantité et prix.
    """
    eid = sortie.entreprise_id or entreprise_id
    if eid is None:
        return []
    user_nom = _nom_utilisateur(user)
    user_obj = user if getattr(user, 'is_authenticated', False) else None
    logs = [
        LogSuppression(
            entreprise_id=eid,
            succursale_id=sortie.succursale_id,
            article=ligne.article,
            article_nom=_nom_article(ligne.article),
            sortie_numero=sortie.pk,
            quantite=ligne.quantite or 0,
            prix_unitaire=ligne.prix_unitaire,
            devise_sigle=(ligne.devise.sigle if ligne.devise_id and ligne.devise else '') or '',
            motif=motif,
            utilisateur=user_obj,
            utilisateur_nom=user_nom,
        )
        for ligne in lignes
    ]
    return LogSuppression.objects.bulk_create(logs)
