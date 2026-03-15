from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission pour les super administrateurs uniquement.
    """
    message = "Seuls les super administrateurs peuvent effectuer cette action."
    
    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and request.user.is_superadmin()
        )


class IsAdmin(permissions.BasePermission):
    """
    Permission pour les administrateurs d'entreprise uniquement.
    """
    message = "Seuls les administrateurs peuvent effectuer cette action."
    
    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and request.user.is_admin()
        )


class IsSuperAdminOrAdmin(permissions.BasePermission):
    """
    Permission pour les super administrateurs ET les administrateurs.
    """
    message = "Vous devez être connecté en tant qu'administrateur."
    
    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and (request.user.is_superadmin() or request.user.is_admin())
        )


class IsSuperAdminOrReadOnlyAdmin(permissions.BasePermission):
    """
    Permission pour super admin (lecture/écriture) ou admin (lecture seule).
    Utilisée pour certaines vues sensibles.
    """
    message = "Accès en écriture réservé aux super administrateurs."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Super admin peut tout faire
        if request.user.is_superadmin():
            return True
        
        # Admin peut seulement lire
        if request.user.is_admin() and request.method in permissions.SAFE_METHODS:
            return True
        
        return False


class IsOwnerOrSuperAdmin(permissions.BasePermission):
    """
    Permission pour le propriétaire de l'objet ou les super administrateurs.
    """
    message = "Vous ne pouvez accéder qu'à vos propres données."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Super admin peut tout voir
        if request.user.is_superadmin():
            return True
        
        # Pour les utilisateurs, ils peuvent voir leur propre profil
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        
        return False


class IsOwnerOrSameEnterprise(permissions.BasePermission):
    """
    Permission pour les objets de la même entreprise ou pour les super administrateurs.
    """
    message = "Vous ne pouvez accéder qu'aux données de votre entreprise."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Super admin peut tout voir
        if request.user.is_superadmin():
            return True
        
        # Admin peut voir les objets de son entreprise
        if request.user.is_admin() and hasattr(obj, 'entreprise'):
            return obj.entreprise == request.user.entreprise
        
        return False