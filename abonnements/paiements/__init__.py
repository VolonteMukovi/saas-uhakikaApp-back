"""Architecture paiement en ligne — gateways et registre."""
from abonnements.paiements.gateways.base import GatewayPaiementBase
from abonnements.paiements.gateways.flexpay import GatewayFlexPay
from abonnements.paiements.gateways.maisha_pay import GatewayMaishaPay
from abonnements.paiements.gateways.serdinate_pay import GatewaySerdinatePay

REGISTRE_GATEWAYS: dict[str, GatewayPaiementBase] = {
    GatewayMaishaPay.code: GatewayMaishaPay(),
    GatewayFlexPay.code: GatewayFlexPay(),
    GatewaySerdinatePay.code: GatewaySerdinatePay(),
}


def get_gateway(code: str) -> GatewayPaiementBase:
    gateway = REGISTRE_GATEWAYS.get(code)
    if not gateway:
        raise ValueError(f'Fournisseur de paiement inconnu : {code}')
    return gateway


def fournisseurs_disponibles() -> list[dict]:
    return [g.infos_publiques() for g in REGISTRE_GATEWAYS.values()]
