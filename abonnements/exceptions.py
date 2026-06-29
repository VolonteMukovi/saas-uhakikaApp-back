"""Exceptions API liées à la licence SaaS."""
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import APIException


class LicenceInactive(APIException):
    """Licence expirée, suspendue ou absente — écriture refusée."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _(
        'Votre abonnement a expiré ou est inactif. Veuillez renouveler pour continuer.'
    )
    default_code = 'licence_inactive'

    def __init__(self, detail=None, etat_licence=None):
        super().__init__(detail=detail)
        self.etat_licence = etat_licence or {}


class FonctionnaliteNonAutorisee(APIException):
    """Fonctionnalité non incluse dans la formule actuelle."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _(
        'Cette fonctionnalité n\'est pas disponible dans votre formule actuelle. '
        'Veuillez passer à une formule supérieure pour l\'utiliser.'
    )
    default_code = 'fonctionnalite_non_autorisee'


class LimiteQuotaAtteinte(APIException):
    """Quota plan atteint (utilisateurs, succursales, etc.)."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Limite de votre formule atteinte.')
    default_code = 'limite_quota_atteinte'

    def __init__(self, detail=None, type_quota=None, maximum=None, actuel=None):
        super().__init__(detail=detail)
        self.type_quota = type_quota
        self.maximum = maximum
        self.actuel = actuel
