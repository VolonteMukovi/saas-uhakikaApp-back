"""Complétion profil utilisateur (flow SaaS)."""
from django.contrib.auth import get_user_model

User = get_user_model()


def profil_est_complet(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    prenom = (user.first_name or '').strip()
    nom = (user.last_name or '').strip()
    return bool(prenom and nom)


def champs_profil_manquants(user) -> list[str]:
    manquants = []
    if not (user.first_name or '').strip():
        manquants.append('first_name')
    if not (user.last_name or '').strip():
        manquants.append('last_name')
    return manquants
