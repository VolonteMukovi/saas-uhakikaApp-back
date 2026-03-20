"""
Authentification JWT avec exposition du contexte tenant (entreprise_id, succursale_id, membership_id)
et request.current_membership pour que is_admin() / is_agent() s'appuient sur Membership.role.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Membership


class JWTAuthenticationWithContext(JWTAuthentication):
    """
    Après authentification JWT, pose sur la requête :
    - request.tenant_id, request.branch_id, request.membership_id
    - request.current_membership (instance Membership) pour le rôle dans le contexte courant.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, validated_token = result
        if hasattr(validated_token, 'get'):
            request.tenant_id = validated_token.get('entreprise_id')
            request.branch_id = validated_token.get('succursale_id')
            request.membership_id = validated_token.get('membership_id')
            mid = request.membership_id
            request.current_membership = (
                Membership.objects.filter(id=mid, user=user, is_active=True)
                .select_related('entreprise', 'default_succursale')
                .first()
            ) if mid else None
        else:
            request.tenant_id = request.branch_id = request.membership_id = None
            request.current_membership = None
        return result
