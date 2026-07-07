from django.urls import path

from inscription.views import (
    ConnexionGoogleView,
    GoogleConfigView,
    InscriptionCompteView,
    StatutOnboardingView,
)
from inscription.views_flow import BootstrapSaasView, CreerEntrepriseMinimaleView, FlowSaasView
from inscription.views_email import (
    ConfirmerEmailRedirectView,
    ModifierEmailVerificationView,
    RenvoyerVerificationView,
    VerifierEmailView,
)

urlpatterns = [
    path('inscription/compte/', InscriptionCompteView.as_view(), name='inscription-compte'),
    path('inscription/google/', ConnexionGoogleView.as_view(), name='inscription-google'),
    path('inscription/google/config/', GoogleConfigView.as_view(), name='inscription-google-config'),
    path('inscription/confirmer-email/', ConfirmerEmailRedirectView.as_view(), name='inscription-confirmer-email'),
    path('inscription/verifier-email/', VerifierEmailView.as_view(), name='inscription-verifier-email'),
    path('inscription/renvoyer-verification/', RenvoyerVerificationView.as_view(), name='inscription-renvoyer-verification'),
    path('inscription/modifier-email-verification/', ModifierEmailVerificationView.as_view(), name='inscription-modifier-email'),
    path('inscription/statut/', StatutOnboardingView.as_view(), name='inscription-statut'),
    path('inscription/flow/', FlowSaasView.as_view(), name='inscription-flow'),
    path('inscription/bootstrap/', BootstrapSaasView.as_view(), name='inscription-bootstrap'),
    path('inscription/entreprise-minimale/', CreerEntrepriseMinimaleView.as_view(), name='inscription-entreprise-minimale'),
]
