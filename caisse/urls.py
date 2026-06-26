from django.urls import include, path
from rest_framework import routers

from caisse.report_views import (
    CaisseMouvementsAPIView,
    CaisseRapportDetailleAPIView,
    CaisseRapportGeneralAPIView,
)
from caisse.session_active_views import SessionActiveAPIView
from caisse.session_views import SessionCaisseViewSet
from caisse.views import MouvementCaisseViewSet, PaiementDetteViewSet, TypeCaisseViewSet

router = routers.DefaultRouter()
router.register(r'mouvements-caisse', MouvementCaisseViewSet)
router.register(r'types-caisse', TypeCaisseViewSet)
router.register(r'paiements-dettes', PaiementDetteViewSet, basename='paiementdette')
router.register(r'sessions-caisse', SessionCaisseViewSet, basename='session-caisse')

caisse_router = routers.DefaultRouter()
caisse_router.register(r'sessions', SessionCaisseViewSet, basename='caisse-sessions')

urlpatterns = [
    path('caisse/session-active/', SessionActiveAPIView.as_view(), name='caisse-session-active'),
    path('caisse/<int:pk>/rapport-general/', CaisseRapportGeneralAPIView.as_view(), name='caisse-rapport-general'),
    path('caisse/<int:pk>/rapport-detaille/', CaisseRapportDetailleAPIView.as_view(), name='caisse-rapport-detaille'),
    path('caisse/<int:pk>/mouvements/', CaisseMouvementsAPIView.as_view(), name='caisse-mouvements'),
    path('caisse/', include(caisse_router.urls)),
    path('', include(router.urls)),
]
