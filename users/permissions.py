from rest_framework import permissions


def is_authenticated_role(user):
    """Utilisateur authentifié avec un rôle reconnu (superadmin, admin, user)."""
    return (
        user
        and user.is_authenticated
        and getattr(user, 'role', None) in ('superadmin', 'admin', 'user')
    )


class IsSuperAdmin(permissions.BasePermission):
    """Super administrateur uniquement (créé via createsuperuser)."""
    message = "Seuls les super administrateurs peuvent effectuer cette action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_superadmin()
        )


class IsAdmin(permissions.BasePermission):
    """Administrateur d'entreprise uniquement."""
    message = "Seuls les administrateurs peuvent effectuer cette action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_admin()
        )


class IsAdminOrUser(permissions.BasePermission):
    """
    Admin ou User (Agent). Pour les vues métier : ventes, stock, rapports, etc.
    L'Admin a CRUD complet sur son entreprise, l'User (agent) idem sauf Entreprise et gestion users.
    """
    message = "Accès réservé aux administrateurs ou aux agents."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin() or request.user.is_agent())
        )


class IsSuperAdminOrAdmin(permissions.BasePermission):
    """Super admin ou Admin (pour vues réservées aux admins, pas aux agents)."""
    message = "Vous devez être connecté en tant qu'administrateur."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_superadmin() or request.user.is_admin())
        )


class IsAdminFullEnterpriseAndUsers(permissions.BasePermission):
    """
    Garantit que l'Admin peut gérer entièrement son entreprise et ses utilisateurs,
    dans le strict respect de la séparation entre entreprises (accès uniquement aux
    données de son entreprise). Utilisé en combinaison avec get_queryset / check_object_permissions.
    """
    message = "Accès réservé aux administrateurs pour la gestion de leur entreprise et de leurs utilisateurs."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_superadmin() or request.user.is_admin())
        )

    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin():
            return True
        if request.user.is_admin() and hasattr(obj, "entreprise_id"):
            return obj.entreprise_id == request.user.entreprise_id
        return False


class IsSuperAdminOrReadOnlyAdmin(permissions.BasePermission):
    """Super admin (lecture/écriture) ou admin (lecture seule)."""
    message = "Accès en écriture réservé aux super administrateurs."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superadmin():
            return True
        if request.user.is_admin() and request.method in permissions.SAFE_METHODS:
            return True
        return False


class IsOwnerOrSuperAdmin(permissions.BasePermission):
    """Propriétaire de l'objet ou super admin (ex. profil utilisateur)."""

    message = "Vous ne pouvez accéder qu'à vos propres données."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin():
            return True
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        return False


class IsOwnerOrSameEnterprise(permissions.BasePermission):
    """Objet de la même entreprise ou super admin."""

    message = "Vous ne pouvez accéder qu'aux données de votre entreprise."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin():
            return True
        if request.user.is_admin() and hasattr(obj, 'entreprise'):
            return obj.entreprise == request.user.entreprise
        if request.user.is_agent() and hasattr(obj, 'entreprise'):
            return obj.entreprise == request.user.entreprise
        return False