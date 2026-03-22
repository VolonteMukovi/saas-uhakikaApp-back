from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils.translation import gettext as _


class EntreprisePermission(permissions.BasePermission):
    """
    Garantit que l'Admin puisse gérer entièrement son entreprise (CRUD complet sur sa seule
    entreprise), tout en respectant la séparation entre entreprises.
    - SuperAdmin : Read (list, retrieve) + Delete uniquement. Pas de Create ni Update.
    - Admin : CRUD complet sur sa propre entreprise uniquement (get_queryset restreint à son entreprise).
    - User (Agent) : lecture seule (GET/HEAD/OPTIONS) sur **son** entreprise (JWT / membership),
      pour le branding (logo, slogan, etc.) — pas de create/update/delete.
    """

    message = "Vous n'avez pas les droits nécessaires sur les entreprises."

    def has_permission(self, request, view):
        """
        Règles d'accès globales sur /entreprises/ :
        - Non authentifié : refusé.
        - Superadmin : lecture (list/retrieve) + delete uniquement, pas de create/update.
        - Admin (via Membership) : CRUD complet sur son entreprise.
        - Utilisateur sans entreprise (aucun Membership) : peut créer sa première entreprise (POST),
          mais n'a pas accès aux autres opérations sur /entreprises/.
        """
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Superadmin : pas de create/update, seulement lecture + delete
        if user.is_superadmin():
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'DELETE')

        # Admin (Membership.role == 'admin') : accès complet
        if user.is_admin(request):
            return True

        # Agent : lecture seule sur le viewset (retrieve/list filtré par get_queryset)
        if user.is_agent(request) and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return user.get_current_membership(request) is not None

        # Utilisateur connecté sans rôle admin : autoriser seulement la création
        if request.method == 'POST':
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin():
            return request.method in ('GET', 'HEAD', 'OPTIONS', 'DELETE')
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        # Membre (admin ou agent) : lecture de sa propre entreprise uniquement
        if request.method in ('GET', 'HEAD', 'OPTIONS') and eid is not None and getattr(obj, 'id', None) == eid:
            if request.user.is_admin(request) or request.user.is_agent(request):
                return True
        if request.user.is_admin(request) and hasattr(obj, 'id'):
            return eid == obj.id
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
        
        if not request.user.is_admin(request):
            raise PermissionDenied(_("Accès réservé aux administrateurs d'entreprise."))
        
        return True


class IsSuperAdminOrAdmin(permissions.BasePermission):
    """Super admin OU admin d'entreprise (pas les agents)."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        if not (request.user.is_superadmin() or request.user.is_admin(request)):
            raise PermissionDenied(_("Accès réservé aux administrateurs."))
        return True


class IsAdminOrUser(permissions.BasePermission):
    """Admin ou User (Agent) : accès aux données métier. SuperAdmin n'a pas accès CRUD aux modèles métier."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        if not (request.user.is_admin(request) or request.user.is_agent(request)):
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
        if request.user.is_admin(request) and request.method in permissions.SAFE_METHODS:
            return True
        
        raise PermissionDenied(_("Accès en écriture réservé aux super administrateurs."))


class IsOwnerOrSuperAdmin(permissions.BasePermission):
    """
    Permission pour vérifier que l'utilisateur accède seulement aux données de son entreprise.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Vous devez être connecté pour accéder à cette ressource."))
        
        return request.user.is_superadmin() or request.user.is_admin(request)
    
    def has_object_permission(self, request, view, obj):
        # Super admin peut accéder à tout
        if request.user.is_superadmin():
            return True
        
        # Admin peut accéder seulement aux objets de son entreprise
        if request.user.is_admin(request):
            user_ent = request.user.get_entreprise(request)
            if not user_ent:
                return False
            if hasattr(obj, 'entreprise_id'):
                return obj.entreprise_id == user_ent.id
            if hasattr(obj, 'get_entreprise_id'):
                return obj.get_entreprise_id() == user_ent.id
            if obj.__class__.__name__ == 'Entreprise':
                return obj.id == user_ent.id
        return False
