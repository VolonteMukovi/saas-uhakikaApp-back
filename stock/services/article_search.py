"""
Recherche d'articles multi-SGBDR, scoping strict entreprise / succursale.

- MySQL : FULLTEXT en NATURAL LANGUAGE MODE (pertinence « souple ») + repli BOOLEAN / LIKE.
- PostgreSQL : pg_trgm (similarity) sur les trois champs, index GIN en migration.
- SQLite : FTS5 externe (stock_article_fts) + préfixes dans MATCH pour rapprocher les saisies.

La sensibilité à la casse dépend de la collation des colonnes (souvent CI).
"""
from __future__ import annotations

import re
from typing import Any

from django.db import DatabaseError, connection
from django.db.utils import OperationalError
from django.db.models import Case, FloatField, Q, QuerySet, Value, When
from django.db.models.expressions import RawSQL

from stock.models import Article

_FTS_SPECIAL_RE = re.compile(r'[~*<>@+-]')

_PG_SIMILARITY_MIN = 0.12

MAX_LIMIT = 100
DEFAULT_LIMIT = 25


def _escape_fts_token(token: str) -> str:
    t = _FTS_SPECIAL_RE.sub(' ', token).strip()
    return t.replace('"', '\\"')


def _tokenize(q: str) -> list[str]:
    return [t for t in q.split() if t]


def _base_qs(entreprise_id: int, succursale_id: int | None) -> QuerySet[Article]:
    base = Article.objects.filter(entreprise_id=entreprise_id).select_related(
        'sous_type_article__type_article',
        'unite',
    )
    if succursale_id is not None:
        base = base.filter(succursale_id=succursale_id)
    return base


def _postgresql_similarity(base: QuerySet[Article], q: str) -> QuerySet[Article]:
    relevance = RawSQL(
        """GREATEST(
            similarity(nom_scientifique, %s),
            similarity(COALESCE(nom_commercial, ''), %s),
            similarity(article_id::text, %s)
        )""",
        [q, q, q],
        output_field=FloatField(),
    )
    return (
        base.annotate(relevance=relevance)
        .filter(relevance__gte=_PG_SIMILARITY_MIN)
        .order_by('-relevance', 'article_id')
    )


def _mysql_fuzzy(base: QuerySet[Article], q: str, tokens: list[str]) -> QuerySet[Article]:
    """
    InnoDB FULLTEXT : la liste des colonnes dans MATCH doit correspondre à un index FULLTEXT.
    Erreur 1191 si l'index manque → repli LIKE (tenant déjà filtré).
    """
    try:
        return _mysql_fuzzy_fulltext(base, q, tokens)
    except OperationalError as e:
        # MySQL 1191: Can't find FULLTEXT index matching the column list
        if len(e.args) >= 1 and e.args[0] == 1191:
            return _fallback_icontains(base, tokens)
        raise


def _mysql_fuzzy_fulltext(base: QuerySet[Article], q: str, tokens: list[str]) -> QuerySet[Article]:
    fts_tokens = [t for t in tokens if len(t) >= 3]
    short_tokens = [t for t in tokens if len(t) < 3]

    q_short = Q()
    for t in short_tokens:
        q_short &= (
            Q(article_id__icontains=t)
            | Q(nom_scientifique__icontains=t)
            | Q(nom_commercial__icontains=t)
        )

    qs_nl = base.annotate(
        relevance=RawSQL(
            'MATCH (nom_scientifique, nom_commercial, article_id) AGAINST (%s IN NATURAL LANGUAGE MODE)',
            [q],
            output_field=FloatField(),
        )
    ).filter(relevance__gt=0)

    if short_tokens:
        qs_nl = qs_nl.filter(q_short)

    if qs_nl.exists():
        return qs_nl.order_by('-relevance', 'article_id')

    if fts_tokens:
        boolean = ' '.join(f'+{_escape_fts_token(t)}*' for t in fts_tokens)
        qs_b = base.annotate(
            relevance=RawSQL(
                'MATCH (nom_scientifique, nom_commercial, article_id) AGAINST (%s IN BOOLEAN MODE)',
                [boolean],
                output_field=FloatField(),
            )
        ).filter(relevance__gt=0)
        if short_tokens:
            qs_b = qs_b.filter(q_short)
        if qs_b.exists():
            return qs_b.order_by('-relevance', 'article_id')

    if short_tokens:
        return base.filter(q_short).annotate(
            relevance=Value(1.0, output_field=FloatField())
        ).order_by('article_id')

    return _fallback_icontains(base, tokens)


def _sanitize_fts5_token(t: str) -> str:
    return re.sub(r'[^\w\u00C0-\u024F]', ' ', t, flags=re.UNICODE).strip()


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


def _sqlite_fts5(
    base: QuerySet[Article],
    entreprise_id: int,
    succursale_id: int | None,
    tokens: list[str],
) -> QuerySet[Article]:
    match_expr = _build_fts5_match(tokens)
    if not match_expr:
        return _fallback_icontains(base, tokens)

    from django.db import connection

    if succursale_id is not None:
        sql = """
            SELECT stock_article.article_id, bm25(stock_article_fts) AS rel
            FROM stock_article
            INNER JOIN stock_article_fts ON stock_article_fts.rowid = stock_article.rowid
            WHERE stock_article.entreprise_id = %s AND stock_article.succursale_id = %s
              AND stock_article_fts MATCH %s
            ORDER BY rel DESC
        """
        params = [entreprise_id, succursale_id, match_expr]
    else:
        sql = """
            SELECT stock_article.article_id, bm25(stock_article_fts) AS rel
            FROM stock_article
            INNER JOIN stock_article_fts ON stock_article_fts.rowid = stock_article.rowid
            WHERE stock_article.entreprise_id = %s AND stock_article_fts MATCH %s
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

    aids = [r[0] for r in rows]
    scores = {r[0]: float(r[1]) for r in rows}

    preserved = Case(
        *[When(article_id=aid, then=Value(scores[aid])) for aid in aids],
        default=Value(0.0),
        output_field=FloatField(),
    )
    return (
        base.filter(article_id__in=aids)
        .annotate(relevance=preserved)
        .order_by('-relevance', 'article_id')
    )


def _fallback_icontains(base: QuerySet[Article], tokens: list[str]) -> QuerySet[Article]:
    q = Q()
    for t in tokens:
        q &= (
            Q(article_id__icontains=t)
            | Q(nom_scientifique__icontains=t)
            | Q(nom_commercial__icontains=t)
        )
    return base.filter(q).annotate(relevance=Value(1.0, output_field=FloatField())).order_by('article_id')


def article_search_queryset(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    q: str,
) -> QuerySet[Article]:
    q = (q or '').strip()
    tokens = _tokenize(q)
    if not tokens:
        return Article.objects.none()

    base = _base_qs(entreprise_id, succursale_id)
    vendor = connection.vendor

    if vendor == 'postgresql':
        return _postgresql_similarity(base, q)
    if vendor == 'mysql':
        return _mysql_fuzzy(base, q, tokens)
    if vendor == 'sqlite':
        return _sqlite_fts5(base, entreprise_id, succursale_id, tokens)

    return _fallback_icontains(base, tokens)


def search_articles(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    q: str,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[Article], dict[str, Any]]:
    limit = min(max(1, limit), MAX_LIMIT)
    offset = max(0, offset)

    qs = article_search_queryset(
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
