from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from stock.models import Devise, Entreprise, TauxChange

AMOUNT_QUANTIZER = Decimal('0.00001')
RATE_QUANTIZER = Decimal('0.00000001')


class CurrencyError(ValidationError):
    pass


def quantize_amount(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(AMOUNT_QUANTIZER, rounding=ROUND_DOWN)


def quantize_rate(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(RATE_QUANTIZER, rounding=ROUND_DOWN)


def get_principal_devise(entreprise_id: int | None) -> Devise | None:
    if not entreprise_id:
        return None
    return Devise.objects.filter(entreprise_id=entreprise_id, est_principal=True).first()


def _config_exchange_rate_sort_key(entry: dict) -> tuple:
    return (
        str(entry.get('effective_at') or ''),
        str(entry.get('created_at') or ''),
        int(entry.get('id') or 0),
    )


def _get_config_exchange_rates(entreprise_id: int | None) -> list[dict]:
    if not entreprise_id:
        return []
    try:
        entreprise = Entreprise.objects.get(pk=entreprise_id)
    except Entreprise.DoesNotExist:
        return []
    try:
        config_data = entreprise.get_config_dict()
    except Exception:
        return []
    integrations = config_data.get('integrations') or {}
    rates = integrations.get('exchange_rates') or []
    return rates if isinstance(rates, list) else []


def _get_config_exchange_rate(
    source_devise: Devise,
    target_devise: Devise,
    *,
    entreprise_id: int | None,
    date_operation=None,
) -> Decimal | None:
    ref_date = date_operation or timezone.now()
    ref_key = _config_exchange_rate_sort_key({
        'effective_at': ref_date.isoformat() if hasattr(ref_date, 'isoformat') else str(ref_date),
    })
    latest_direct = None
    latest_inverse = None

    for entry in _get_config_exchange_rates(entreprise_id):
        if entry.get('is_active', True) is False:
            continue
        entry_key = _config_exchange_rate_sort_key(entry)
        if entry_key > ref_key:
            continue
        source_id = entry.get('source_devise_id')
        target_id = entry.get('target_devise_id')
        try:
            rate = quantize_rate(entry.get('rate'))
        except Exception:
            continue
        if rate <= 0:
            continue
        if source_id == source_devise.pk and target_id == target_devise.pk:
            if latest_direct is None or entry_key > _config_exchange_rate_sort_key(latest_direct):
                latest_direct = entry
        elif source_id == target_devise.pk and target_id == source_devise.pk:
            if latest_inverse is None or entry_key > _config_exchange_rate_sort_key(latest_inverse):
                latest_inverse = entry

    if latest_direct is not None:
        return quantize_rate(latest_direct.get('rate'))
    if latest_inverse is not None:
        inverse_rate = quantize_rate(latest_inverse.get('rate'))
        if inverse_rate <= 0:
            return None
        return quantize_rate(Decimal('1') / inverse_rate)
    return None


def get_exchange_rate(
    source_devise: Devise | None,
    target_devise: Devise | None,
    *,
    entreprise_id: int | None,
    date_operation=None,
    explicit_rate: Decimal | int | float | str | None = None,
) -> Decimal:
    if source_devise is None or target_devise is None:
        raise CurrencyError('Devise source ou cible manquante pour la conversion.')
    if source_devise.pk == target_devise.pk:
        return Decimal('1.00000000')
    if explicit_rate is not None and str(explicit_rate).strip() != '':
        rate = quantize_rate(explicit_rate)
        if rate <= 0:
            raise CurrencyError('Le taux de change fourni doit etre strictement positif.')
        return rate

    ref_date = date_operation or timezone.now()
    direct = (
        TauxChange.objects.filter(
            entreprise_id=entreprise_id,
            devise_source=source_devise,
            devise_cible=target_devise,
            is_active=True,
            date_application__lte=ref_date,
        )
        .order_by('-date_application', '-id')
        .first()
    )
    if direct:
        return quantize_rate(direct.taux)

    inverse = (
        TauxChange.objects.filter(
            entreprise_id=entreprise_id,
            devise_source=target_devise,
            devise_cible=source_devise,
            is_active=True,
            date_application__lte=ref_date,
        )
        .order_by('-date_application', '-id')
        .first()
    )
    if inverse and inverse.taux:
        return quantize_rate(Decimal('1') / Decimal(str(inverse.taux)))

    config_rate = _get_config_exchange_rate(
        source_devise,
        target_devise,
        entreprise_id=entreprise_id,
        date_operation=date_operation,
    )
    if config_rate is not None:
        return config_rate

    raise CurrencyError('Aucun taux de change actif n est defini pour cette devise.')


def convert_amount(amount, rate: Decimal) -> Decimal:
    return (Decimal(str(amount or 0)) * Decimal(str(rate))).quantize(AMOUNT_QUANTIZER, rounding=ROUND_DOWN)


def build_conversion_snapshot(
    *,
    entreprise_id: int | None,
    amount,
    devise_source: Devise | None,
    devise_reference: Devise | None = None,
    date_operation=None,
    explicit_rate: Decimal | int | float | str | None = None,
) -> dict:
    amount_decimal = quantize_amount(amount)
    devise_ref = devise_reference or get_principal_devise(entreprise_id)
    if devise_source is None:
        raise CurrencyError('Toute operation financiere doit avoir une devise.')
    if devise_ref is None:
        raise CurrencyError('Aucune devise principale n est configuree pour cette entreprise.')
    rate = get_exchange_rate(
        devise_source,
        devise_ref,
        entreprise_id=entreprise_id,
        date_operation=date_operation,
        explicit_rate=explicit_rate,
    )
    return {
        'devise_reference': devise_ref,
        'taux_change': rate,
        'montant_reference': convert_amount(amount_decimal, rate),
    }


def assert_caisse_devise_compatible(type_caisse, devise: Devise | None) -> None:
    if type_caisse is None or devise is None:
        return
    if type_caisse.devise_id and type_caisse.devise_id != devise.id:
        raise CurrencyError('La caisse selectionnee n accepte pas cette devise.')
