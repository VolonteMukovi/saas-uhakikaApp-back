"""
Configuration JSON par entreprise (apparence rapports, POS, UI…).
"""
from __future__ import annotations

import copy
import json
from typing import Any

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

DEFAULT_ENTREPRISE_CONFIG: dict[str, Any] = {
    'version': 1,
    'document_appearance': {},
    'reports': {},
    'pos': {},
    'ui': {},
    'notifications': {},
    'integrations': {},
}

VALID_REPORT_TYPES = frozenset({
    'inventaire',
    'fiche_stock',
    'bon_entree',
    'bon_achat',
    'ventes',
    'clients_dettes',
    'clients_dettes_general',
    'journal',
    'etat_caisse',
    'compte_courant',
})

KNOWN_ROOT_KEYS = frozenset({
    'version',
    'updated_at',
    'updated_by_user_id',
    'document_appearance',
    'reports',
    'pos',
    'ui',
    'notifications',
    'integrations',
})

MAX_CONFIG_BYTES = 512_000


def default_entreprise_config() -> dict:
    return copy.deepcopy(DEFAULT_ENTREPRISE_CONFIG)


def parse_config_raw(raw: str | None) -> dict:
    if not raw or not str(raw).strip():
        return default_entreprise_config()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError({'detail': _('Configuration JSON invalide.')}) from exc
    if not isinstance(data, dict):
        raise ValidationError({'detail': _('Configuration JSON invalide.')})
    return data


def validate_config_size(data: dict) -> None:
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    if len(encoded.encode('utf-8')) > MAX_CONFIG_BYTES:
        raise ValidationError({'detail': _('Configuration trop volumineuse.')})


def validate_document_appearance_value(report_type: str, value: Any) -> None:
    if report_type not in VALID_REPORT_TYPES:
        raise ValidationError({'detail': _('Type de rapport inconnu : %(type)s') % {'type': report_type}})
    if not isinstance(value, dict):
        raise ValidationError({
            'document_appearance': _('Chaque configuration de rapport doit être un objet JSON.'),
        })
    rt = value.get('report_type')
    if rt is not None and rt != report_type:
        raise ValidationError({
            'document_appearance': _(
                'Le champ report_type doit correspondre à la clé du rapport (%(expected)s).'
            ) % {'expected': report_type},
        })


def validate_document_appearance_section(section: Any) -> None:
    if section is None:
        return
    if not isinstance(section, dict):
        raise ValidationError({
            'document_appearance': _('document_appearance doit être un objet JSON.'),
        })
    for key, value in section.items():
        validate_document_appearance_value(key, value)


def validate_config_patch(patch: dict) -> None:
    if not isinstance(patch, dict):
        raise ValidationError({'detail': _('Le corps de la requête doit être un objet JSON.')})
    for key in patch:
        if key not in KNOWN_ROOT_KEYS:
            raise ValidationError({'detail': _('Clé de configuration inconnue : %(key)s') % {'key': key}})
    if 'document_appearance' in patch:
        validate_document_appearance_section(patch['document_appearance'])


def merge_config_dict(current: dict, patch: dict, *, user_id: int | None = None) -> dict:
    from datetime import datetime, timezone

    validate_config_patch(patch)
    merged = copy.deepcopy(current)
    for key, value in patch.items():
        if key in ('version', 'updated_at', 'updated_by_user_id'):
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            if key == 'document_appearance':
                section = {**merged.get(key, {})}
                for report_key, report_val in value.items():
                    validate_document_appearance_value(report_key, report_val)
                    if isinstance(section.get(report_key), dict) and isinstance(report_val, dict):
                        section[report_key] = {**section[report_key], **report_val}
                    else:
                        section[report_key] = copy.deepcopy(report_val)
                merged[key] = section
            else:
                merged[key] = {**merged.get(key, {}), **value}
        else:
            merged[key] = copy.deepcopy(value)
    merged['version'] = int(merged.get('version') or 1)
    merged['updated_at'] = datetime.now(timezone.utc).isoformat()
    if user_id is not None:
        merged['updated_by_user_id'] = user_id
    validate_config_size(merged)
    return merged


def serialize_config_dict(data: dict) -> str:
    validate_config_size(data)
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def replace_document_appearance(
    current: dict,
    report_type: str,
    data: dict,
    *,
    user_id: int | None = None,
) -> dict:
    from datetime import datetime, timezone

    validate_document_appearance_value(report_type, data)
    merged = copy.deepcopy(current)
    payload = copy.deepcopy(data)
    payload['report_type'] = report_type
    section = dict(merged.get('document_appearance') or {})
    section[report_type] = payload
    merged['document_appearance'] = section
    merged['version'] = int(merged.get('version') or 1)
    merged['updated_at'] = datetime.now(timezone.utc).isoformat()
    if user_id is not None:
        merged['updated_by_user_id'] = user_id
    validate_config_size(merged)
    return merged


def remove_document_appearance(
    current: dict,
    report_type: str,
    *,
    user_id: int | None = None,
) -> dict:
    from datetime import datetime, timezone

    if report_type not in VALID_REPORT_TYPES:
        raise ValidationError({'detail': _('Type de rapport inconnu : %(type)s') % {'type': report_type}})
    merged = copy.deepcopy(current)
    section = dict(merged.get('document_appearance') or {})
    section.pop(report_type, None)
    merged['document_appearance'] = section
    merged['version'] = int(merged.get('version') or 1)
    merged['updated_at'] = datetime.now(timezone.utc).isoformat()
    if user_id is not None:
        merged['updated_by_user_id'] = user_id
    validate_config_size(merged)
    return merged
