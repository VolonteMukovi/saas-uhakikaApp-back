"""
Pagination professionnelle pour toute l'API.
Par défaut : 25 enregistrements par page, du plus récent au plus ancien.
Le client peut modifier le nombre par page via ?page_size=50 (plafonné à max_limit).
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination par défaut : 25 résultats par page, modifiable via query param."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200
