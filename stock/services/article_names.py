"""Normalisation des noms d'articles pour détection de doublons (tenant-safe)."""


def normalize_nom_scientifique(value: str | None) -> str:
    """
    Normalise pour comparaison stricte : insensible à la casse, espaces repliés.
    """
    if value is None:
        return ''
    s = ' '.join(str(value).split())
    return s.casefold()


def article_duplicate_exists(
    entreprise_id,
    succursale_id,
    norm: str,
    *,
    exclude_article_id=None,
) -> bool:
    """
    True si un article du même tenant a déjà un nom scientifique équivalent (normalisé).
    Import local du modèle pour éviter les imports circulaires.
    """
    from stock.models import Article

    qs = Article.objects.filter(entreprise_id=entreprise_id).only('article_id', 'nom_scientifique')
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)
    else:
        qs = qs.filter(succursale_id__isnull=True)
    if exclude_article_id is not None:
        qs = qs.exclude(pk=exclude_article_id)
    for row in qs.iterator(chunk_size=200):
        if normalize_nom_scientifique(row.nom_scientifique) == norm:
            return True
    return False
