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
from inscription.views_onboarding import (
    ActiverEspaceRedirectView,
    OnboardingActivateWorkspaceView,
    OnboardingCompanyView,
    OnboardingCompleteView,
    OnboardingMarkWelcomeSeenView,
    OnboardingProfileView,
    OnboardingResendActivationView,
    OnboardingStatusView,
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
    path('onboarding/status/', OnboardingStatusView.as_view(), name='onboarding-status'),
    path('onboarding/profile/', OnboardingProfileView.as_view(), name='onboarding-profile'),
    path('onboarding/company/', OnboardingCompanyView.as_view(), name='onboarding-company'),
    path('onboarding/complete/', OnboardingCompleteView.as_view(), name='onboarding-complete'),
    path('onboarding/mark-welcome-seen/', OnboardingMarkWelcomeSeenView.as_view(), name='onboarding-mark-welcome-seen'),
    path('onboarding/activate-workspace/', OnboardingActivateWorkspaceView.as_view(), name='onboarding-activate-workspace'),
    path('onboarding/resend-activation/', OnboardingResendActivationView.as_view(), name='onboarding-resend-activation'),
    path('onboarding/activer-espace/', ActiverEspaceRedirectView.as_view(), name='onboarding-activer-espace'),
]
