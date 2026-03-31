"""
Permissions portail commandes : administrateur (vue globale tenant) ou client (ses données uniquement).
Les agents (`Membership.role=user`) n’ont pas accès aux commandes portail.
"""
from rest_framework import permissions
from django.utils.translation import gettext as _


class IsClientAuthenticated(permissions.BasePermission):
    """Client portail authentifié (`request.client` défini par `ClientJWTAuthentication`)."""

    message = _("Authentification client requise.")

    def has_permission(self, request, view):
        return bool(getattr(request, "client", None)) and bool(getattr(request, "client_membership", None))


class IsStaffOrClientCommande(permissions.BasePermission):
    """
    - Client portail : ses commandes.
    - Administrateur ou employé (agent) : commandes du tenant.
    """

    message = _("Accès réservé au client, à un administrateur ou à un employé de l’entreprise.")

    def has_permission(self, request, view):
        if getattr(request, "client", None):
            return True
        u = request.user
        if not u or not u.is_authenticated:
            return False
        return u.is_admin(request) or u.is_agent(request)


class IsStaffEntrepriseForCommandes(permissions.BasePermission):
    """Administrateur ou employé (pas le portail client)."""

    message = _("Accès réservé aux administrateurs et employés de l’entreprise.")

    def has_permission(self, request, view):
        if getattr(request, "client", None):
            return False
        u = request.user
        if not u or not u.is_authenticated:
            return False
        return u.is_admin(request) or u.is_agent(request)


class IsAdminOrClientDestroyCommande(permissions.BasePermission):
    """Suppression : client (ses commandes) ou administrateur uniquement (pas l’agent)."""

    message = _("Suppression réservée au client ou à un administrateur.")

    def has_permission(self, request, view):
        if getattr(request, "client", None):
            return True
        u = request.user
        return bool(u and u.is_authenticated and u.is_admin(request))
