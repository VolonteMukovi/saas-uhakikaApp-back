"""
Interface commune des gateways de paiement (Maisha Pay, FlexPay, SerdinatePay).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.http import HttpRequest


@dataclass
class NotificationPaiement:
    """Résultat normalisé d'une notification gateway."""

    reference_interne: str
    reference_externe: str
    statut: str  # confirme | echec
    montant: Decimal | None = None
    devise: str | None = None
    brut: dict | None = None


class GatewayPaiementBase(ABC):
    code: str = ''
    nom: str = ''

    @abstractmethod
    def est_configure(self) -> bool:
        """True si les clés API / secrets webhook sont présents."""

    @abstractmethod
    def infos_publiques(self) -> dict:
        """Infos affichables au frontend (sans secrets)."""

    @abstractmethod
    def initier_session(self, paiement) -> dict:
        """
        Démarre une session de paiement côté gateway.
        Retourne au minimum : mode, url_paiement (optionnel), reference_externe, sandbox.
        """

    @abstractmethod
    def verifier_signature_webhook(self, request: HttpRequest) -> bool:
        """Vérifie l'authenticité de la notification entrante."""

    @abstractmethod
    def parser_notification(self, payload: dict[str, Any]) -> NotificationPaiement:
        """Convertit le payload gateway en notification normalisée."""

    def mode_sandbox(self) -> bool:
        from django.conf import settings
        return bool(getattr(settings, 'PAIEMENT_GATEWAY_SANDBOX', False))
