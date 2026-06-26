"""Helpers partagés pour les opérations financières (stock, order, import)."""
from __future__ import annotations

from typing import Optional

from caisse.services.caisse_defaut import CaisseError, parse_type_caisse_id_from_payload


def extract_type_caisse_id(request_data) -> Optional[int]:
    """Extrait type_caisse_id / caisse_id / caisse depuis le body API."""
    try:
        return parse_type_caisse_id_from_payload(request_data)
    except CaisseError:
        return None
