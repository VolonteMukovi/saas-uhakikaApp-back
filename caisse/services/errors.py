"""Formatage des erreurs métier caisse pour l'API."""
from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError


def validation_error_message(exc: Exception) -> str:
    """
    Extrait un message lisible sans crochets ni représentation liste Python.

    ``str(ValidationError('msg'))`` renvoie ``['msg']`` — à éviter côté API.
    """
    if isinstance(exc, DjangoValidationError):
        if getattr(exc, 'message_dict', None):
            parts: list[str] = []
            for vals in exc.message_dict.values():
                if isinstance(vals, list):
                    parts.extend(str(v) for v in vals)
                else:
                    parts.append(str(vals))
            if parts:
                return '; '.join(parts)
        messages = getattr(exc, 'messages', None)
        if messages:
            if isinstance(messages, list):
                return '; '.join(str(m) for m in messages)
            return str(messages)
    return str(exc)
