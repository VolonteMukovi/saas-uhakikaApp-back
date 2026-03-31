from django.urls import include, path
from rest_framework import routers

from .client_auth_views import (
    client_portal_dashboard,
    client_portal_login,
    client_portal_refresh,
    client_portal_select_context,
)
from .client_portal_articles import client_portal_articles_search
from .client_portal_viewsets import ClientPortalDetteViewSet, ClientPortalSortieViewSet
from .commande_views import CommandeViewSet
from .views import FournisseurViewSet, LotViewSet, FraisLotViewSet, LotItemViewSet

router = routers.DefaultRouter()
router.register(r"fournisseurs", FournisseurViewSet, basename="fournisseur")
router.register(r"lots", LotViewSet)
router.register(r"frais-lots", FraisLotViewSet, basename="frais-lot")
router.register(r"lot-items", LotItemViewSet, basename="lot-item")
router.register(r"commandes", CommandeViewSet, basename="commande")
router.register(r"client-portal/dettes", ClientPortalDetteViewSet, basename="client-portal-dette")
router.register(r"client-portal/ventes", ClientPortalSortieViewSet, basename="client-portal-vente")

urlpatterns = [
    path("client-auth/login/", client_portal_login, name="client-portal-login"),
    path("client-auth/refresh/", client_portal_refresh, name="client-portal-refresh"),
    path("client-auth/select-context/", client_portal_select_context, name="client-portal-select-context"),
    path("client-portal/dashboard/", client_portal_dashboard, name="client-portal-dashboard"),
    path("client-portal/articles/search/", client_portal_articles_search, name="client-portal-articles-search"),
    path("", include(router.urls)),
]

