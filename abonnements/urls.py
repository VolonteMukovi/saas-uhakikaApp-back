from django.urls import include, path
from rest_framework.routers import DefaultRouter

from abonnements.views import (
    DemandeInstallationPriveeView,
    DemanderAbonnementView,
    FormuleAbonnementViewSet,
    InfoInstallationPriveeView,
    MesLimitesView,
    MonAbonnementView,
    PlateformeAbonnementViewSet,
    PlateformeJournalViewSet,
)
from abonnements.views_paiement import (
    FournisseursPaiementView,
    InitierPaiementView,
    SimulerWebhookPaiementView,
    StatutPaiementView,
    WebhookFlexPayView,
    WebhookMaishaPayView,
    WebhookSerdinatePayView,
)

router = DefaultRouter()
router.register(r'abonnements/formules', FormuleAbonnementViewSet, basename='formules-abonnement')
router.register(r'plateforme/abonnements', PlateformeAbonnementViewSet, basename='plateforme-abonnements')
router.register(r'plateforme/journal-licences', PlateformeJournalViewSet, basename='plateforme-journal-licences')

urlpatterns = [
    path('abonnements/mon-abonnement/', MonAbonnementView.as_view(), name='mon-abonnement'),
    path('abonnements/mes-limites/', MesLimitesView.as_view(), name='mes-limites'),
    path('abonnements/paiements/fournisseurs/', FournisseursPaiementView.as_view(), name='paiements-fournisseurs'),
    path('abonnements/paiements/initier/', InitierPaiementView.as_view(), name='paiements-initier'),
    path('abonnements/paiements/simuler/', SimulerWebhookPaiementView.as_view(), name='paiements-simuler'),
    path('abonnements/paiements/statut/<str:reference_interne>/', StatutPaiementView.as_view(), name='paiements-statut'),
    path('abonnements/paiements/webhooks/maisha-pay/', WebhookMaishaPayView.as_view(), name='webhook-maisha-pay'),
    path('abonnements/paiements/webhooks/flexpay/', WebhookFlexPayView.as_view(), name='webhook-flexpay'),
    path('abonnements/paiements/webhooks/serdinate-pay/', WebhookSerdinatePayView.as_view(), name='webhook-serdinate-pay'),
    path('abonnements/demander/', DemanderAbonnementView.as_view(), name='demander-abonnement'),
    path('abonnements/installation-privee/info/', InfoInstallationPriveeView.as_view(), name='installation-privee-info'),
    path('abonnements/installation-privee/demander/', DemandeInstallationPriveeView.as_view(), name='installation-privee-demander'),
    path('', include(router.urls)),
]
