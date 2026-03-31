"""
JWT dédié aux clients (portail) — distinct des tokens utilisateurs (staff).
Contexte : `ClientEntreprise` (membership) pour entreprise + succursale préférée.
"""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

ACCESS_HOURS = 12
REFRESH_DAYS = 14
ALGO = "HS256"


def _now():
    return datetime.now(timezone.utc)


def issue_client_tokens(client, membership):
    """
    Retourne (access_token, refresh_token) pour un `stock.Client`
    dans le contexte d'un lien `ClientEntreprise` (entreprise + succursale).
    """
    from stock.models import ClientEntreprise

    if not isinstance(membership, ClientEntreprise):
        raise TypeError("membership must be ClientEntreprise")
    if membership.client_id != client.pk:
        raise ValueError("membership client mismatch")

    now = _now()
    access_payload = {
        "sub": f"client:{client.pk}",
        "typ": "client_access",
        "client_id": client.pk,
        "membership_id": membership.pk,
        "entreprise_id": membership.entreprise_id,
        "succursale_id": membership.succursale_id,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_HOURS),
    }
    refresh_payload = {
        "sub": f"client:{client.pk}",
        "typ": "client_refresh",
        "client_id": client.pk,
        "membership_id": membership.pk,
        "entreprise_id": membership.entreprise_id,
        "succursale_id": membership.succursale_id,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_DAYS),
    }
    secret = settings.SECRET_KEY
    access = jwt.encode(access_payload, secret, algorithm=ALGO)
    refresh = jwt.encode(refresh_payload, secret, algorithm=ALGO)
    if isinstance(access, bytes):
        access = access.decode("utf-8")
    if isinstance(refresh, bytes):
        refresh = refresh.decode("utf-8")
    return access, refresh


def decode_client_token(token, expected_typ):
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGO],
        options={"require": ["exp", "iat", "sub", "typ", "client_id", "entreprise_id", "membership_id"]},
    )
    if payload.get("typ") != expected_typ:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def refresh_client_access(refresh_token: str):
    """À partir d'un refresh client, émet un nouveau couple (access, refresh)."""
    payload = decode_client_token(refresh_token, "client_refresh")
    from stock.models import Client, ClientEntreprise

    client = Client.objects.filter(pk=payload["client_id"]).first()
    membership = ClientEntreprise.objects.filter(
        pk=payload["membership_id"],
        client_id=payload["client_id"],
    ).first()
    if not client or not membership:
        raise jwt.InvalidTokenError("client invalid")
    if membership.entreprise_id != payload.get("entreprise_id"):
        raise jwt.InvalidTokenError("context invalid")
    return issue_client_tokens(client, membership)
