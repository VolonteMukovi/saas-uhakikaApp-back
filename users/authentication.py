"""
Authentification JWT avec exposition du contexte tenant (entreprise_id, succursale_id, membership_id).
"""
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthenticationWithContext(JWTAuthentication):
    """
    Après authentification JWT, pose sur la requête le contexte multi-tenant
    lu depuis les claims : request.tenant_id, request.branch_id, request.membership_id.
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
        else:
            request.tenant_id = request.branch_id = request.membership_id = None
        return result
