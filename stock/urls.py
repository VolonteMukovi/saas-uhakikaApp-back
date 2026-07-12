from rest_framework import routers
from .views import *
from .inventaire_views import InventaireSessionViewSet
from django.urls import path, include

router = routers.DefaultRouter()
router.register(r'entreprises', EntrepriseViewSet)
router.register(r'succursales', SuccursaleViewSet, basename='succursale')
router.register(r'unites', UniteViewSet)
router.register(r'conditionnements-articles', ConditionnementArticleViewSet, basename='conditionnement-article')
router.register(r'codes-barres-articles', CodeBarresArticleViewSet, basename='code-barres-article')
router.register(r'stock/code-barres/lookup', CodeBarresLookupView, basename='code-barres-lookup')
router.register(r'typearticles', TypeArticleViewSet)
router.register(r'soustypearticles', SousTypeArticleViewSet)
router.register(r'articles', ArticleViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'entrees', EntreeViewSet)
router.register(r'ligneentrees', LigneEntreeViewSet)
router.register(r'prix-conditionnement-entrees', PrixConditionnementEntreeViewSet, basename='prix-conditionnement-entree')
router.register(r'sorties', SortieViewSet)
router.register(r'lignesorties', LigneSortieViewSet)
router.register(r'rapports', RapportViewSet, basename='rapport')
router.register(r'devises', DeviseViewSet)
router.register(r'taux-change', TauxChangeViewSet, basename='taux-change')
router.register(r'clients', ClientViewSet)
router.register(r'client-entreprises', ClientEntrepriseViewSet, basename='client-entreprise')
router.register(r'dettes', DetteClientViewSet)
router.register(r'inventaires', InventaireSessionViewSet, basename='inventaire')


urlpatterns = [
    path('taux-change/', taux_change_collection, name='taux-change-collection'),
    path('', include(router.urls)),
]
