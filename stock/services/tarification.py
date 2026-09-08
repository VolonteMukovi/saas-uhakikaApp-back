"""
Catalogue de tarification : tous les articles du tenant avec leur dernier prix de vente.

Les articles jamais approvisionnés apparaissent aussi, avec prix = null (placeholder UI).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from django.db.models import Prefetch, Q

from stock.models import Article, ConditionnementArticle, LigneEntree
from stock.services.requisition import PRIX_PLACEHOLDER, designation_article

# Réexport pour l'API / docs frontend
__all__ = ['PRIX_PLACEHOLDER', 'build_queryset_tarification', 'build_tarification_page']

MONEY_QUANT = Decimal('0.00001')


def _dec(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return None


def _fmt_price(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value.quantize(MONEY_QUANT))


def _fmt_qty(value) -> str | None:
    if value is None:
        return None
    try:
        return str(Decimal(str(value)).quantize(MONEY_QUANT))
    except Exception:  # noqa: BLE001
        return None


def _categorie(article: Article) -> str | None:
    st = getattr(article, 'sous_type_article', None)
    if not st:
        return None
    ta = getattr(st, 'type_article', None)
    parts = []
    if ta and ta.libelle:
        parts.append(ta.libelle)
    if st.libelle:
        parts.append(st.libelle)
    return ' / '.join(parts) if parts else None


def _serialize_devise(devise) -> dict[str, Any] | None:
    if devise is None:
        return None
    return {
        'id': devise.pk,
        'sigle': devise.sigle,
        'symbole': devise.symbole,
        'nom': devise.nom,
    }


def _devise_sigle(devise: dict[str, Any] | None) -> str | None:
    if not devise:
        return None
    return devise.get('sigle') or devise.get('symbole') or None


def _build_latest_price_maps(article_ids: Iterable[str]) -> tuple[dict, dict]:
    """
    Retourne :
    - by_article[article_id] = {prix_vente_base, prix_vente_conditionnement, date, conditionnement_id, devise}
    - by_cond[(article_id, conditionnement_id)] = {prix_vente_conditionnement, date, devise}
    """
    ids = list(article_ids)
    by_article: dict[str, dict] = {}
    by_cond: dict[tuple[str, int | None], dict] = {}
    if not ids:
        return by_article, by_cond

    rows = (
        LigneEntree.objects.filter(article_id__in=ids)
        .select_related('entree', 'devise')
        .order_by('article_id', '-entree__date_op', '-date_entree', '-id')
        .only(
            'id',
            'article_id',
            'conditionnement_id',
            'prix_vente',
            'prix_vente_conditionnement',
            'date_entree',
            'entree_id',
            'devise_id',
            'devise__id',
            'devise__sigle',
            'devise__symbole',
            'devise__nom',
        )
    )

    for row in rows.iterator(chunk_size=500):
        aid = row.article_id
        date_op = getattr(getattr(row, 'entree', None), 'date_op', None) or row.date_entree
        devise = _serialize_devise(getattr(row, 'devise', None))
        pv = _dec(row.prix_vente)
        pvc = _dec(row.prix_vente_conditionnement)
        if pvc is None or pvc <= 0:
            pvc = pv if pv and pv > 0 else None
        if pv is not None and pv <= 0:
            pv = None
        if pvc is not None and pvc <= 0:
            pvc = None

        if aid not in by_article:
            by_article[aid] = {
                'prix_vente_unitaire_base': pv,
                'prix_vente_conditionnement': pvc,
                'date_dernier_prix': date_op,
                'conditionnement_id': row.conditionnement_id,
                'ligne_entree_id': row.pk,
                'devise': devise,
            }

        key = (aid, row.conditionnement_id)
        if key not in by_cond and row.conditionnement_id is not None:
            by_cond[key] = {
                'prix_vente_conditionnement': pvc,
                'prix_vente_unitaire_base': pv,
                'date_dernier_prix': date_op,
                'ligne_entree_id': row.pk,
                'devise': devise,
            }

    return by_article, by_cond


def _prix_conditionnement(
    *,
    article_id: str,
    cond: ConditionnementArticle,
    by_article: dict,
    by_cond: dict,
) -> dict[str, Any]:
    """Dernier prix packing ; fallback base × multiplicateur si packing jamais entré."""
    hit = by_cond.get((article_id, cond.pk))
    prix = hit['prix_vente_conditionnement'] if hit else None
    date = hit['date_dernier_prix'] if hit else None
    source = 'ligne_entree' if hit else None
    devise = hit.get('devise') if hit else None

    if prix is None:
        base_info = by_article.get(article_id) or {}
        base = base_info.get('prix_vente_unitaire_base')
        mult = _dec(cond.multiplicateur_base) or Decimal('1')
        if base is not None and mult > 0:
            prix = (base * mult).quantize(MONEY_QUANT)
            date = base_info.get('date_dernier_prix')
            source = 'derive_unitaire_base'
            devise = base_info.get('devise')

    manquant = prix is None
    return {
        'id': cond.pk,
        'nom': cond.nom,
        'multiplicateur_base': _fmt_qty(cond.multiplicateur_base) or '1.00000',
        'est_defaut': bool(cond.est_defaut),
        'prix_vente_conditionnement': _fmt_price(prix),
        'prix_vente_affiche': PRIX_PLACEHOLDER if manquant else _fmt_price(prix),
        'prix_manquant': manquant,
        'date_dernier_prix': date.isoformat() if date else None,
        'source_prix': source,
        'devise': devise,
        'devise_sigle': _devise_sigle(devise),
    }


def serialize_article_tarification(
    article: Article,
    *,
    by_article: dict,
    by_cond: dict,
) -> dict[str, Any]:
    info = by_article.get(article.article_id) or {}
    prix_base = info.get('prix_vente_unitaire_base')
    manquant = prix_base is None
    devise = info.get('devise')
    stock = getattr(article, 'stock', None)
    unite = article.unite if article.unite_id else None

    conditionnements = [
        _prix_conditionnement(
            article_id=article.article_id,
            cond=cond,
            by_article=by_article,
            by_cond=by_cond,
        )
        for cond in article.conditionnements.all()
    ]

    return {
        'article_id': article.article_id,
        'nom_scientifique': article.nom_scientifique or '',
        'nom_commercial': article.nom_commercial or '',
        'designation': designation_article(article),
        'categorie': _categorie(article),
        'unite': (
            {'id': unite.pk, 'libelle': unite.libelle}
            if unite else None
        ),
        'unite_stock_base': (unite.libelle if unite else '') or '',
        'succursale_id': article.succursale_id,
        'stock_actuel': _fmt_qty(getattr(stock, 'Qte', None)),
        'seuil_alerte': _fmt_qty(getattr(stock, 'seuilAlert', None)),
        'prix_vente_unitaire_base': _fmt_price(prix_base),
        'prix_vente_affiche': PRIX_PLACEHOLDER if manquant else _fmt_price(prix_base),
        'prix_manquant': manquant,
        'date_dernier_prix': (
            info['date_dernier_prix'].isoformat()
            if info.get('date_dernier_prix') else None
        ),
        'source_prix': 'ligne_entree' if info else None,
        'devise': devise,
        'devise_sigle': _devise_sigle(devise),
        'conditionnements': conditionnements,
    }


def build_queryset_tarification(
    *,
    entreprise_id: int,
    succursale_id: int | None = None,
    search: str | None = None,
    prix_manquant: bool | None = None,
    type_article_id: int | None = None,
    sous_type_article_id: int | None = None,
):
    """Queryset articles tenant, prêt pour pagination puis sérialisation."""
    qs = (
        Article.objects.filter(entreprise_id=entreprise_id)
        .select_related(
            'unite',
            'sous_type_article',
            'sous_type_article__type_article',
            'stock',
        )
        .prefetch_related(
            Prefetch(
                'conditionnements',
                queryset=ConditionnementArticle.objects.order_by('-est_defaut', 'nom', 'id'),
            ),
        )
        .order_by('nom_scientifique', 'article_id')
    )
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)
    if sous_type_article_id is not None:
        qs = qs.filter(sous_type_article_id=sous_type_article_id)
    if type_article_id is not None:
        qs = qs.filter(sous_type_article__type_article_id=type_article_id)
    if search:
        q = search.strip()
        if q:
            qs = qs.filter(
                Q(article_id__icontains=q)
                | Q(nom_scientifique__icontains=q)
                | Q(nom_commercial__icontains=q)
            )

    # Filtre prix manquant : appliqué après annotation via ids (évite N+1 SQL complexe).
    # On laisse la vue appeler `filter_articles_by_prix_manquant` si besoin.
    return qs


def filter_articles_by_prix_manquant(
    articles: list[Article],
    by_article: dict,
    *,
    prix_manquant: bool,
) -> list[Article]:
    if prix_manquant:
        return [a for a in articles if a.article_id not in by_article or by_article[a.article_id].get('prix_vente_unitaire_base') is None]
    return [a for a in articles if a.article_id in by_article and by_article[a.article_id].get('prix_vente_unitaire_base') is not None]


def build_tarification_page(
    articles: list[Article],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sérialise une page d'articles + résumé global de la page."""
    by_article, by_cond = _build_latest_price_maps(a.article_id for a in articles)
    results = [
        serialize_article_tarification(a, by_article=by_article, by_cond=by_cond)
        for a in articles
    ]
    sans = sum(1 for r in results if r['prix_manquant'])
    resume = {
        'nombre_articles': len(results),
        'avec_prix': len(results) - sans,
        'sans_prix': sans,
        'placeholder_prix': PRIX_PLACEHOLDER,
    }
    return results, resume
