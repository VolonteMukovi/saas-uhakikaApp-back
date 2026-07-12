"""Rate limiting chatbot par utilisateur."""
from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _


def check_rate_limit(user_id: int) -> tuple[bool, str | None]:
    max_per_minute = int(getattr(settings, 'CHATBOT_RATE_LIMIT_PER_MINUTE', 20))
    key = f'chatbot:rl:{user_id}'
    count = cache.get(key, 0)
    if count >= max_per_minute:
        return False, _('Trop de questions en peu de temps. Réessayez dans une minute.')
    cache.set(key, count + 1, 60)
    return True, None
