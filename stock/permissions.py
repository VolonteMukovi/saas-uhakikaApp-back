from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils.translation import gettext as _


class EntreprisePermission(permissions.BasePermission):
    """
    Garantit que l'Admin puisse gérer entièrement son entreprise (CRUD complet sur sa seule
    entreprise), tout en respectant la séparation entre entreprises.
    - SuperAdmin : Read (list, retrieve) + Delete uniquement. Pas de Create ni Update.
    - Admin : CRUD complet sur sa propre entreprise uniquement (get_queryset restreint à son entreprise).
    - User (Agent) : aucun accès.
    """

    message = "Vous n'avez pas les droits nécessaires sur les entreprises."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superadmin():
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'DELETE')
        if request.user.is_admin():
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin():
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'DELETE')
        if request.user.is_admin() and hasattr(obj, 'id'):
            return getattr(request.user, 'entreprise_id', None) == obj.id
        return False


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission pour les super administrateurs uniquement.
    Permet la gestion complète du système.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        
        if not (request.user.is_superadmin() or request.user.is_superuser):
            raise PermissionDenied(_("Accès réservé aux super administrateurs."))
        
        return True


class IsAdmin(permissions.BasePermission):
    """
    Permission pour les administrateurs d'entreprise.
    Permet la gestion de leur entreprise uniquement.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        
        if not request.user.is_admin():
            raise PermissionDenied(_("Accès réservé aux administrateurs d'entreprise."))
        
        return True


class IsSuperAdminOrAdmin(permissions.BasePermission):
    """Super admin OU admin d'entreprise (pas les agents)."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        if not (request.user.is_superadmin() or request.user.is_admin()):
            raise PermissionDenied(_("Accès réservé aux administrateurs."))
        return True


class IsAdminOrUser(permissions.BasePermission):
    """Admin ou User (Agent) : accès aux données métier. SuperAdmin n'a pas accès CRUD aux modèles métier."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        if not (request.user.is_admin() or request.user.is_agent()):
            raise PermissionDenied(_("Accès réservé aux administrateurs ou aux agents de l'entreprise."))
        return True


class IsSuperAdminOrReadOnlyAdmin(permissions.BasePermission):
    """
    Permission pour super admin (lecture/écriture) ou admin (lecture seule).
    Utilisée pour certaines vues sensibles.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        
        # Super admin peut tout faire
        if request.user.is_superadmin():
            return True
        
        # Admin peut seulement lire
        if request.user.is_admin() and request.method in permissions.SAFE_METHODS:
            return True
        
        raise PermissionDenied(_("Accès en écriture réservé aux super administrateurs."))


class IsOwnerOrSuperAdmin(permissions.BasePermission):
    """
    Permission pour vérifier que l'utilisateur accède seulement aux données de son entreprise.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        
        return request.user.is_superadmin() or request.user.is_admin()
    
    def has_object_permission(self, request, view, obj):
        # Super admin peut accéder à tout
        if request.user.is_superadmin():
            return True
        
        # Admin peut accéder seulement aux objets de son entreprise
        if request.user.is_admin():
            # Vérifier si l'objet appartient à l'entreprise de l'utilisateur
            if hasattr(obj, 'entreprise'):
                return obj.entreprise == request.user.entreprise
            # Si l'objet est une entreprise elle-même
            elif obj.__class__.__name__ == 'Entreprise':
                return obj == request.user.entreprise
        
        return False
