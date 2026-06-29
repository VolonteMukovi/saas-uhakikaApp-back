"""Gateway SerdinatePay (préparation intégration)."""
from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal

from django.conf import settings
from django.http import HttpRequest

from abonnements.paiements.gateways.base import GatewayPaiementBase, NotificationPaiement


class GatewaySerdinatePay(GatewayPaiementBase):
    code = 'serdinate_pay'
    nom = 'SerdinatePay'

    def _api_key(self) -> str:
        return getattr(settings, 'SERDI_PAY_API_KEY', '') or ''

    def _webhook_secret(self) -> str:
        return getattr(settings, 'SERDI_PAY_WEBHOOK_SECRET', '') or ''

    def est_configure(self) -> bool:
        return bool(self._api_key() and self._webhook_secret())

    def infos_publiques(self) -> dict:
        return {
            'code': self.code,
            'nom': self.nom,
            'configure': self.est_configure(),
            'sandbox': self.mode_sandbox(),
            'modes_supportes': ['mobile_money', 'carte'],
        }

    def initier_session(self, paiement) -> dict:
        base_url = getattr(settings, 'PAIEMENT_RETURN_BASE_URL', 'https://uhakikaapp.store')
        callback = f"{getattr(settings, 'PAIEMENT_WEBHOOK_BASE_URL', '')}/api/abonnements/paiements/webhooks/serdinate-pay/"
        if self.est_configure() and not self.mode_sandbox():
            return {
                'mode': 'redirect',
                'url_paiement': f'{base_url}/paiement/en-attente?ref={paiement.reference_interne}',
                'reference_externe': f'SERDI-{paiement.reference_interne}',
                'sandbox': False,
                'callback_url': callback,
            }
        return {
            'mode': 'sandbox',
            'url_paiement': f'{base_url}/paiement/sandbox?ref={paiement.reference_interne}&gateway=serdinate_pay',
            'reference_externe': f'SANDBOX-SERDI-{paiement.reference_interne}',
            'sandbox': True,
            'message': 'Mode sandbox SerdinatePay.',
            'callback_url': callback,
        }

    def verifier_signature_webhook(self, request: HttpRequest) -> bool:
        secret = self._webhook_secret()
        if not secret:
            return self.mode_sandbox()
        signature = request.headers.get('X-Serdinate-Signature', '')
        attendu = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, attendu)

    def parser_notification(self, payload: dict) -> NotificationPaiement:
        statut_raw = (payload.get('event') or payload.get('status') or '').lower()
        statut = 'confirme' if statut_raw in ('payment.success', 'success', 'paid', 'confirme') else 'echec'
        montant = payload.get('amount') or payload.get('montant')
        return NotificationPaiement(
            reference_interne=str(payload.get('order_id') or payload.get('reference_interne') or ''),
            reference_externe=str(payload.get('payment_id') or payload.get('reference_externe') or ''),
            statut=statut,
            montant=Decimal(str(montant)) if montant is not None else None,
            devise=payload.get('currency') or payload.get('devise'),
            brut=payload,
        )
