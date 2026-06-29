from rest_framework.permissions import BasePermission, IsAuthenticated


class EstSuperAdminPlateforme(BasePermission):
    """Super administrateur UHAKIKAAPP (is_superuser)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


class AEntrepriseContexte(BasePermission):
    """Utilisateur authentifié avec une entreprise dans le contexte JWT."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        return eid is not None
