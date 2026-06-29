"""
Permissions réutilisables pour limiter l'accès selon la licence / formule.
"""
from rest_framework.permissions import BasePermission
from django.utils.translation import gettext as _

from abonnements.exceptions import FonctionnaliteNonAutorisee, LicenceInactive
from abonnements.services.licence import build_etat_licence, fonctionnalite_autorisee


class LicenceActiveRequise(BasePermission):
    """
    Bloque si l'entreprise n'a pas de licence active (essai ou payant).
    Les superadmins plateforme sont exemptés.
    """

    message = _('Votre abonnement a expiré ou est inactif. Veuillez renouveler pour continuer.')

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        if not eid:
            return False
        etat = getattr(request, 'etat_licence', None) or build_etat_licence(eid)
        if etat.get('est_actif'):
            return True
        raise LicenceInactive(detail=etat.get('message') or self.message, etat_licence=etat)


class FonctionnaliteLicenceRequise(BasePermission):
    """
    À utiliser sur une vue : permission_classes = [..., FonctionnaliteLicenceRequise]
    et view.fonctionnalite_licence = 'vente_credit'
    """

    message = _(
        'Cette fonctionnalité n\'est pas disponible dans votre formule actuelle. '
        'Veuillez passer à une formule supérieure pour l\'utiliser.'
    )

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        cle = getattr(view, 'fonctionnalite_licence', None)
        if not cle:
            return True
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        if not eid:
            return False
        if not fonctionnalite_autorisee(eid, cle):
            raise FonctionnaliteNonAutorisee()
        return True
