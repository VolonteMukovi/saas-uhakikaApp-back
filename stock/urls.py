from rest_framework import routers
from .views import *
from django.urls import path, include

router = routers.DefaultRouter()
router.register(r'entreprises', EntrepriseViewSet)
router.register(r'succursales', SuccursaleViewSet, basename='succursale')
router.register(r'unites', UniteViewSet)
router.register(r'typearticles', TypeArticleViewSet)
router.register(r'soustypearticles', SousTypeArticleViewSet)
router.register(r'articles', ArticleViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'entrees', EntreeViewSet)
router.register(r'ligneentrees', LigneEntreeViewSet)
router.register(r'sorties', SortieViewSet)
router.register(r'lignesorties', LigneSortieViewSet)
router.register(r'rapports', RapportViewSet, basename='rapport')
router.register(r'mouvements-caisse', MouvementCaisseViewSet)
router.register(r'devises', DeviseViewSet)
router.register(r'clients', ClientViewSet)
router.register(r'dettes', DetteClientViewSet)
router.register(r'paiements-dettes', PaiementDetteViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
