from django.urls import include, path
from rest_framework import routers

from caisse.session_active_views import SessionActiveAPIView
from caisse.session_views import SessionCaisseViewSet
from caisse.views import MouvementCaisseViewSet, PaiementDetteViewSet, TypeCaisseViewSet

router = routers.DefaultRouter()
router.register(r'mouvements-caisse', MouvementCaisseViewSet)
router.register(r'types-caisse', TypeCaisseViewSet)
router.register(r'paiements-dettes', PaiementDetteViewSet, basename='paiementdette')
router.register(r'sessions-caisse', SessionCaisseViewSet, basename='session-caisse')

urlpatterns = [
    path('caisse/session-active/', SessionActiveAPIView.as_view(), name='caisse-session-active'),
    path('', include(router.urls)),
]
