"""
Pagination API Uhakika.

- Par défaut (frontend actuel) : ``?page=1&page_size=200`` → format DRF classique
  ``{ count, next, previous, results }``.
- Mode curseur (CURSOR.md règle 7) : ``?cursor=...`` →
  ``{ next_cursor, previous_cursor, results }``.
"""
from __future__ import annotations

import base64
import math
from urllib.parse import parse_qs, urlparse

from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response


def _cursor_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = parse_qs(urlparse(url).query)
    for key in ('cursor', 'next_cursor', 'previous_cursor'):
        vals = parsed.get(key)
        if vals:
            return vals[0]
    return None


def _encode_list_cursor(index: int) -> str:
    return base64.urlsafe_b64encode(f'list:{index}'.encode()).decode()


def _decode_list_cursor(cursor: str) -> int | None:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        if raw.startswith('list:'):
            return max(0, int(raw.split(':', 1)[1]))
    except Exception:
        return None
    return None


class UhakikaPageNumberPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200


class UhakikaCursorPagination(CursorPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200
    ordering = '-pk'
    cursor_query_param = 'cursor'

    _list_next_cursor = None
    _list_previous_cursor = None
    _used_list_pagination = False

    def paginate_queryset(self, queryset, request, view=None):
        if isinstance(queryset, list):
            return self._paginate_list(queryset, request)
        self._used_list_pagination = False
        return super().paginate_queryset(queryset, request, view)

    def _paginate_list(self, items, request):
        self._used_list_pagination = True
        self._list_next_cursor = None
        self._list_previous_cursor = None
        page_size = self.get_page_size(request)
        cursor = request.query_params.get(self.cursor_query_param)
        start = _decode_list_cursor(cursor) if cursor else 0
        if start is None:
            start = 0
        end = start + page_size
        page = items[start:end]
        if start > 0:
            self._list_previous_cursor = _encode_list_cursor(max(0, start - page_size))
        if end < len(items):
            self._list_next_cursor = _encode_list_cursor(end)
        return page

    def get_paginated_response(self, data):
        if self._used_list_pagination:
            return Response({
                'next_cursor': self._list_next_cursor,
                'previous_cursor': self._list_previous_cursor,
                'results': data,
            })
        return Response({
            'next_cursor': _cursor_from_url(self.get_next_link()),
            'previous_cursor': _cursor_from_url(self.get_previous_link()),
            'results': data,
        })


class UhakikaPagination(UhakikaPageNumberPagination):
    """
    Route automatique :
    - ``?cursor=`` sans ``page`` → curseur opaque ;
    - sinon → pagination par page (compatibilité frontend existant).
    """

    _mode = 'page'
    _cursor_paginator: UhakikaCursorPagination | None = None
    _list_page_meta: dict | None = None

    def paginate_queryset(self, queryset, request, view=None):
        use_cursor = bool(request.query_params.get('cursor')) and not request.query_params.get('page')
        if use_cursor:
            self._mode = 'cursor'
            self._cursor_paginator = UhakikaCursorPagination()
            self._cursor_paginator.page_size = self.get_page_size(request)
            return self._cursor_paginator.paginate_queryset(queryset, request, view)

        if isinstance(queryset, list):
            self._mode = 'list_page'
            return self._paginate_list_by_page(queryset, request)

        self._mode = 'page'
        self._cursor_paginator = None
        self._list_page_meta = None
        return super().paginate_queryset(queryset, request, view)

    def _paginate_list_by_page(self, items, request):
        page_size = self.get_page_size(request)
        try:
            page_number = int(request.query_params.get(self.page_query_param, 1))
        except (TypeError, ValueError):
            page_number = 1
        page_number = max(1, page_number)
        count = len(items)
        total_pages = max(1, math.ceil(count / page_size)) if count else 1
        start = (page_number - 1) * page_size
        end = start + page_size
        self._list_page_meta = {
            'count': count,
            'page': page_number,
            'page_size': page_size,
            'total_pages': total_pages,
            'has_next': end < count,
            'has_previous': page_number > 1,
        }
        return items[start:end]

    def get_paginated_response(self, data):
        if self._mode == 'cursor' and self._cursor_paginator is not None:
            return self._cursor_paginator.get_paginated_response(data)
        if self._mode == 'list_page' and self._list_page_meta is not None:
            meta = self._list_page_meta
            return Response({
                'count': meta['count'],
                'page': meta['page'],
                'page_size': meta['page_size'],
                'total_pages': meta['total_pages'],
                'has_next': meta['has_next'],
                'has_previous': meta['has_previous'],
                'next': None,
                'previous': None,
                'results': data,
            })
        return super().get_paginated_response(data)


StandardResultsSetPagination = UhakikaPagination
