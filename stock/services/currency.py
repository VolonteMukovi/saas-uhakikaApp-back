from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_DOWN

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
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


def _as_aware_datetime(value) -> datetime | None:
    """Normalise une date / datetime / string ISO en datetime aware."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, time.min)
    else:
        raw = str(value).strip()
        dt = parse_datetime(raw)
        if dt is None:
            d = parse_date(raw[:10]) if len(raw) >= 10 else parse_date(raw)
            if d is None:
                return None
            dt = datetime.combine(d, time.min)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _ref_operation_datetime(date_operation=None) -> datetime:
    ref = date_operation or timezone.now()
    parsed = _as_aware_datetime(ref)
    return parsed or timezone.now()


def _config_exchange_rate_sort_key(entry: dict) -> tuple:
    effective = _as_aware_datetime(entry.get('effective_at')) or datetime.min.replace(tzinfo=timezone.utc)
    created = _as_aware_datetime(entry.get('created_at')) or datetime.min.replace(tzinfo=timezone.utc)
    try:
        entry_id = int(entry.get('id') or 0)
    except (TypeError, ValueError):
        entry_id = 0
    return (effective, created, entry_id)


def _coerce_devise_id(value) -> int | None:
    try:
        if value is None or value == '':
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _rate_is_applicable(entry: dict, ref_dt: datetime) -> bool:
    """
    Un taux date-only « YYYY-MM-DD » doit s'appliquer toute la journée locale,
    même si le serveur est encore sur le jour UTC précédent.
    """
    effective = _as_aware_datetime(entry.get('effective_at'))
    if effective is None:
        return True
    ref_local = timezone.localtime(ref_dt).date()
    effective_local = timezone.localtime(effective).date()
    return effective_local <= ref_local


def _inverse_of_rate(rate: Decimal | int | float | str) -> Decimal:
    """Inverse exact (sans troncature précoce) : 1/2300 doit rester utilisable pour CDF→USD."""
    inverse_rate = Decimal('1') / Decimal(str(rate))
    if inverse_rate <= 0:
        raise CurrencyError('Le taux de change inverse est invalide.')
    return inverse_rate


def _pick_best_rate_entry(
    candidates: list[dict],
    *,
    ref_dt: datetime,
) -> dict | None:
    """Préfère un taux déjà applicable, sinon le dernier actif (aligné sur l'UI « Actif »)."""
    if not candidates:
        return None
    applicable = [e for e in candidates if _rate_is_applicable(e, ref_dt)]
    pool = applicable or candidates
    return max(pool, key=_config_exchange_rate_sort_key)


def _get_config_exchange_rate(
    source_devise: Devise,
    target_devise: Devise,
    *,
    entreprise_id: int | None,
    date_operation=None,
) -> Decimal | None:
    ref_dt = _ref_operation_datetime(date_operation)
    direct_candidates: list[dict] = []
    inverse_candidates: list[dict] = []
    source_pk = source_devise.pk
    target_pk = target_devise.pk

    for entry in _get_config_exchange_rates(entreprise_id):
        if entry.get('is_active', True) is False:
            continue
        source_id = _coerce_devise_id(entry.get('source_devise_id'))
        target_id = _coerce_devise_id(entry.get('target_devise_id'))
        try:
            rate = quantize_rate(entry.get('rate'))
        except Exception:
            continue
        if rate <= 0:
            continue
        if source_id == source_pk and target_id == target_pk:
            direct_candidates.append(entry)
        elif source_id == target_pk and target_id == source_pk:
            inverse_candidates.append(entry)

    latest_direct = _pick_best_rate_entry(direct_candidates, ref_dt=ref_dt)
    if latest_direct is not None:
        return quantize_rate(latest_direct.get('rate'))

    latest_inverse = _pick_best_rate_entry(inverse_candidates, ref_dt=ref_dt)
    if latest_inverse is not None:
        inverse_rate = quantize_rate(latest_inverse.get('rate'))
        if inverse_rate <= 0:
            return None
        return _inverse_of_rate(inverse_rate)
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

    ref_dt = _ref_operation_datetime(date_operation)
    # Comparer sur le jour local pour éviter qu’un taux « date du jour » client
    # (midnight local) soit rejeté quand le serveur est encore sur le jour UTC précédent.
    ref_day = timezone.localtime(ref_dt).date()

    direct_qs = TauxChange.objects.filter(
        entreprise_id=entreprise_id,
        devise_source=source_devise,
        devise_cible=target_devise,
        is_active=True,
    )
    direct = (
        direct_qs.filter(date_application__date__lte=ref_day)
        .order_by('-date_application', '-id')
        .first()
    ) or direct_qs.order_by('-date_application', '-id').first()
    if direct:
        return quantize_rate(direct.taux)

    inverse_qs = TauxChange.objects.filter(
        entreprise_id=entreprise_id,
        devise_source=target_devise,
        devise_cible=source_devise,
        is_active=True,
    )
    inverse = (
        inverse_qs.filter(date_application__date__lte=ref_day)
        .order_by('-date_application', '-id')
        .first()
    ) or inverse_qs.order_by('-date_application', '-id').first()
    if inverse and inverse.taux:
        return _inverse_of_rate(inverse.taux)

    config_rate = _get_config_exchange_rate(
        source_devise,
        target_devise,
        entreprise_id=entreprise_id,
        date_operation=date_operation,
    )
    if config_rate is not None:
        return config_rate

    raise CurrencyError(
        f'Aucun taux de change actif n est defini pour convertir '
        f'{source_devise.sigle} vers {target_devise.sigle} '
        f'(ni dans le sens inverse).'
    )


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
    """Conservé pour compatibilité : la conversion inter-devises est gérée dans creer_mouvement_caisse."""
    return
