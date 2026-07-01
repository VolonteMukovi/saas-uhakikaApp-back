from django.urls import path

from inscription.views import (
    ConnexionGoogleView,
    GoogleConfigView,
    InscriptionCompteView,
    StatutOnboardingView,
)
from inscription.views_flow import BootstrapSaasView, CreerEntrepriseMinimaleView, FlowSaasView

urlpatterns = [
    path('inscription/compte/', InscriptionCompteView.as_view(), name='inscription-compte'),
    path('inscription/google/', ConnexionGoogleView.as_view(), name='inscription-google'),
    path('inscription/google/config/', GoogleConfigView.as_view(), name='inscription-google-config'),
    path('inscription/statut/', StatutOnboardingView.as_view(), name='inscription-statut'),
    path('inscription/flow/', FlowSaasView.as_view(), name='inscription-flow'),
    path('inscription/bootstrap/', BootstrapSaasView.as_view(), name='inscription-bootstrap'),
    path('inscription/entreprise-minimale/', CreerEntrepriseMinimaleView.as_view(), name='inscription-entreprise-minimale'),
]
