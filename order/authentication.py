"""
Authentification Bearer JWT pour les clients du portail (claim `typ=client_access`).
Pose `request.client` et `request.client_membership` (`ClientEntreprise`).
"""
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from stock.models import Client, ClientEntreprise


class ClientJWTAuthentication(BaseAuthentication):
    """Valide `Authorization: Bearer <access>` émis par `issue_client_tokens`."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION")
        if not header or not header.startswith(f"{self.keyword} "):
            return None
        raw = header[len(self.keyword) + 1 :].strip()
        if not raw:
            return None
        try:
            payload = jwt.decode(
                raw,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"require": ["exp", "typ", "client_id", "entreprise_id", "membership_id"]},
            )
        except jwt.PyJWTError:
            return None
        if payload.get("typ") != "client_access":
            return None
        try:
            client = Client.objects.get(pk=payload["client_id"])
            membership = ClientEntreprise.objects.select_related("entreprise", "succursale").get(
                pk=payload["membership_id"],
                client_id=client.pk,
            )
        except (Client.DoesNotExist, ClientEntreprise.DoesNotExist):
            raise AuthenticationFailed("Client ou contexte introuvable.")
        if membership.entreprise_id != payload.get("entreprise_id"):
            raise AuthenticationFailed("Contexte entreprise invalide.")
        if "succursale_id" in payload and payload.get("succursale_id") != membership.succursale_id:
            raise AuthenticationFailed("Contexte succursale invalide (rafraîchissez le jeton).")
        request.client = client
        request.client_membership = membership
        return (None, raw)
