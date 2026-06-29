"""Réponse JWT alignée sur POST /api/auth/ (connexion classique)."""
import time

from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from stock.serializers import entreprise_public_read_dict
from users.models import Membership
from users.views import _add_context_to_token, _succursales_for_membership


def build_jwt_login_response(user, request=None):
    """
    Tokens + profil utilisateur + contexte tenant (premier membership actif).
    Même structure que CustomTokenObtainPairSerializer.
    """
    refresh = RefreshToken.for_user(user)
    refresh['session_start'] = int(time.time())

    first_m = (
        Membership.objects
        .select_related('entreprise', 'default_succursale')
        .filter(user_id=user.id, is_active=True)
        .order_by('entreprise_id', 'id')
        .first()
    )
    _add_context_to_token(refresh, first_m)

    if api_settings.UPDATE_LAST_LOGIN:
        update_last_login(None, user)

    memberships = (
        Membership.objects
        .select_related('entreprise', 'default_succursale')
        .filter(user_id=user.id, is_active=True)
        .order_by('entreprise_id', 'id')
    )
    entreprises = []
    for m in memberships:
        entreprises.append({
            'membership_id': m.id,
            'entreprise': entreprise_public_read_dict(m.entreprise, request),
            'role': m.role,
            'default_branch_id': m.default_succursale_id,
            'succursales': _succursales_for_membership(m),
        })

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'entreprise': entreprises[0]['entreprise'] if entreprises else None,
        'enterprises': entreprises,
        'succursales': _succursales_for_membership(first_m) if first_m else [],
        'default_succursale_id': first_m.default_succursale_id if first_m else None,
    }

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': user_data,
    }
