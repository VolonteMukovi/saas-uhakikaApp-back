"""Gateway FlexPay (préparation intégration)."""
from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal

from django.conf import settings
from django.http import HttpRequest

from abonnements.paiements.gateways.base import GatewayPaiementBase, NotificationPaiement


class GatewayFlexPay(GatewayPaiementBase):
    code = 'flexpay'
    nom = 'FlexPay'

    def _api_key(self) -> str:
        return getattr(settings, 'FLEXPAY_API_KEY', '') or ''

    def _webhook_secret(self) -> str:
        return getattr(settings, 'FLEXPAY_WEBHOOK_SECRET', '') or ''

    def est_configure(self) -> bool:
        return bool(self._api_key() and self._webhook_secret())

    def infos_publiques(self) -> dict:
        return {
            'code': self.code,
            'nom': self.nom,
            'configure': self.est_configure(),
            'sandbox': self.mode_sandbox(),
            'modes_supportes': ['mobile_money'],
        }

    def initier_session(self, paiement) -> dict:
        base_url = getattr(settings, 'PAIEMENT_RETURN_BASE_URL', 'https://uhakikaapp.store')
        callback = f"{getattr(settings, 'PAIEMENT_WEBHOOK_BASE_URL', '')}/api/abonnements/paiements/webhooks/flexpay/"
        if self.est_configure() and not self.mode_sandbox():
            return {
                'mode': 'redirect',
                'url_paiement': f'{base_url}/paiement/en-attente?ref={paiement.reference_interne}',
                'reference_externe': f'FLEX-{paiement.reference_interne}',
                'sandbox': False,
                'callback_url': callback,
            }
        return {
            'mode': 'sandbox',
            'url_paiement': f'{base_url}/paiement/sandbox?ref={paiement.reference_interne}&gateway=flexpay',
            'reference_externe': f'SANDBOX-FLEX-{paiement.reference_interne}',
            'sandbox': True,
            'message': 'Mode sandbox FlexPay.',
            'callback_url': callback,
        }

    def verifier_signature_webhook(self, request: HttpRequest) -> bool:
        secret = self._webhook_secret()
        if not secret:
            return self.mode_sandbox()
        signature = request.headers.get('X-FlexPay-Signature', '')
        attendu = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, attendu)

    def parser_notification(self, payload: dict) -> NotificationPaiement:
        statut_raw = (payload.get('status') or payload.get('code') or '').lower()
        statut = 'confirme' if statut_raw in ('00', 'success', 'paid', 'ok', 'confirme') else 'echec'
        montant = payload.get('amount') or payload.get('montant')
        return NotificationPaiement(
            reference_interne=str(payload.get('reference') or payload.get('reference_interne') or ''),
            reference_externe=str(payload.get('transactionRef') or payload.get('reference_externe') or ''),
            statut=statut,
            montant=Decimal(str(montant)) if montant is not None else None,
            devise=payload.get('currency') or payload.get('devise'),
            brut=payload,
        )
