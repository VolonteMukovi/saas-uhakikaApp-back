"""
Recherche de clients multi-SGBDR (même stratégie que article_search).
Champs : id, nom, téléphone, adresse, email. Scoping entreprise / succursale.
"""
from __future__ import annotations

import re
from typing import Any

from django.db import DatabaseError, connection
from django.db.utils import OperationalError
from django.db.models import Case, FloatField, Q, QuerySet, Value, When
from django.db.models.expressions import RawSQL

from django.db.models import Q

from stock.models import Client

_FTS_SPECIAL_RE = re.compile(r'[~*<>@+-]')
_PG_SIMILARITY_MIN = 0.12
_MAX_LIMIT = 100
_DEFAULT_LIMIT = 25


def _escape_fts_token(token: str) -> str:
    t = _FTS_SPECIAL_RE.sub(' ', token).strip()
    return t.replace('"', '\\"')


def _tokenize(q: str) -> list[str]:
    return [t for t in q.split() if t]


def _sanitize_fts5_token(t: str) -> str:
    return re.sub(r'[^\w\u00C0-\u024F@.+]', ' ', t, flags=re.UNICODE).strip()


def _build_fts5_match(tokens: list[str]) -> str:
    parts: list[str] = []
    for t in tokens:
        s = _sanitize_fts5_token(t)
        if not s:
            continue
        if len(s) >= 2:
            parts.append(f'"{s}"*')
        else:
            parts.append(f'"{s}"')
    return ' AND '.join(parts) if parts else ''


def _base_qs(entreprise_id: int, succursale_id: int | None) -> QuerySet[Client]:
    base = Client.objects.filter(liens_entreprise__entreprise_id=entreprise_id).distinct()
    if succursale_id is not None:
        base = base.filter(
            Q(liens_entreprise__entreprise_id=entreprise_id)
            & (
                Q(liens_entreprise__succursale_id=succursale_id)
                | Q(liens_entreprise__succursale__isnull=True)
            )
        ).distinct()
    return base


def _postgresql_similarity(base: QuerySet[Client], q: str) -> QuerySet[Client]:
    relevance = RawSQL(
        """GREATEST(
            COALESCE(similarity(nom, %s), 0),
            COALESCE(similarity(COALESCE(telephone, ''), %s), 0),
            COALESCE(similarity(COALESCE(adresse, ''), %s), 0),
            COALESCE(similarity(COALESCE(email, ''), %s), 0),
            COALESCE(similarity(id::text, %s), 0)
        )""",
        [q, q, q, q, q],
        output_field=FloatField(),
    )
    return (
        base.annotate(relevance=relevance)
        .filter(relevance__gte=_PG_SIMILARITY_MIN)
        # `id` becomes ambiguous once the base queryset joins ClientEntreprise.
        .order_by('-relevance', 'pk')
    )


def _mysql_fuzzy_fulltext(base: QuerySet[Client], q: str, tokens: list[str]) -> QuerySet[Client]:
    fts_tokens = [t for t in tokens if len(t) >= 3]
    short_tokens = [t for t in tokens if len(t) < 3]

    q_short = Q()
    for t in short_tokens:
        q_short &= (
            Q(id__icontains=t)
            | Q(nom__icontains=t)
            | Q(telephone__icontains=t)
            | Q(adresse__icontains=t)
            | Q(email__icontains=t)
        )

    qs_nl = base.annotate(
        relevance=RawSQL(
            # `id` becomes ambiguous once `base` joins `ClientEntreprise`.
            # Searching by id is already covered by the `q_short` / fallback icontains filters.
            'MATCH (nom, telephone, adresse, email) AGAINST (%s IN NATURAL LANGUAGE MODE)',
            [q],
            output_field=FloatField(),
        )
    ).filter(relevance__gt=0)

    if short_tokens:
        qs_nl = qs_nl.filter(q_short)

    if qs_nl.exists():
        return qs_nl.order_by('-relevance', 'pk')

    if fts_tokens:
        boolean = ' '.join(f'+{_escape_fts_token(t)}*' for t in fts_tokens)
        qs_b = base.annotate(
            relevance=RawSQL(
                'MATCH (nom, telephone, adresse, email) AGAINST (%s IN BOOLEAN MODE)',
                [boolean],
                output_field=FloatField(),
            )
        ).filter(relevance__gt=0)
        if short_tokens:
            qs_b = qs_b.filter(q_short)
        if qs_b.exists():
            return qs_b.order_by('-relevance', 'pk')

    if short_tokens:
        return base.filter(q_short).annotate(
            relevance=Value(1.0, output_field=FloatField())
        ).order_by('pk')

    return _fallback_icontains(base, tokens)


def _mysql_fuzzy(base: QuerySet[Client], q: str, tokens: list[str]) -> QuerySet[Client]:
    try:
        return _mysql_fuzzy_fulltext(base, q, tokens)
    except OperationalError as e:
        if len(e.args) >= 1 and e.args[0] == 1191:
            return _fallback_icontains(base, tokens)
        raise


def _sqlite_fts5(
    base: QuerySet[Client],
    entreprise_id: int,
    succursale_id: int | None,
    tokens: list[str],
) -> QuerySet[Client]:
    match_expr = _build_fts5_match(tokens)
    if not match_expr:
        return _fallback_icontains(base, tokens)

    from django.db import connection

    if succursale_id is not None:
        sql = """
            SELECT stock_client.id, bm25(stock_client_fts) AS rel
            FROM stock_client
            INNER JOIN stock_client_fts ON stock_client_fts.rowid = stock_client.rowid
            WHERE stock_client.entreprise_id = %s AND stock_client.succursale_id = %s
              AND stock_client_fts MATCH %s
            ORDER BY rel DESC
        """
        params = [entreprise_id, succursale_id, match_expr]
    else:
        sql = """
            SELECT stock_client.id, bm25(stock_client_fts) AS rel
            FROM stock_client
            INNER JOIN stock_client_fts ON stock_client_fts.rowid = stock_client.rowid
            WHERE stock_client.entreprise_id = %s AND stock_client_fts MATCH %s
            ORDER BY rel DESC
        """
        params = [entreprise_id, match_expr]

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    except DatabaseError:
        return _fallback_icontains(base, tokens)
    if not rows:
        return _fallback_icontains(base, tokens)

    ids = [r[0] for r in rows]
    scores = {r[0]: float(r[1]) for r in rows}

    preserved = Case(
        *[When(id=cid, then=Value(scores[cid])) for cid in ids],
        default=Value(0.0),
        output_field=FloatField(),
    )
    return (
        base.filter(id__in=ids).annotate(relevance=preserved).order_by('-relevance', 'pk')
    )


def _fallback_icontains(base: QuerySet[Client], tokens: list[str]) -> QuerySet[Client]:
    q = Q()
    for t in tokens:
        q &= (
            Q(id__icontains=t)
            | Q(nom__icontains=t)
            | Q(telephone__icontains=t)
            | Q(adresse__icontains=t)
            | Q(email__icontains=t)
        )
    return base.filter(q).annotate(relevance=Value(1.0, output_field=FloatField())).order_by('pk')


def client_search_queryset(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    q: str,
) -> QuerySet[Client]:
    q = (q or '').strip()
    tokens = _tokenize(q)
    if not tokens:
        return Client.objects.none()

    base = _base_qs(entreprise_id, succursale_id)
    vendor = connection.vendor

    if vendor == 'postgresql':
        return _postgresql_similarity(base, q)
    if vendor == 'mysql':
        return _mysql_fuzzy(base, q, tokens)
    if vendor == 'sqlite':
        # FTS5 historique sur stock_client.entreprise_id : périmètre désormais via ClientEntreprise.
        return _fallback_icontains(base, tokens)

    return _fallback_icontains(base, tokens)


def search_clients(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    q: str,
    limit: int = _DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[Client], dict[str, Any]]:
    limit = min(max(1, limit), _MAX_LIMIT)
    offset = max(0, offset)

    qs = client_search_queryset(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        q=q,
    )
    total = qs.count()
    page = list(qs[offset : offset + limit])
    return page, {
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': offset + len(page) < total,
    }


DEFAULT_LIMIT = _DEFAULT_LIMIT
MAX_LIMIT = _MAX_LIMIT
