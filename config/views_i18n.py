"""
Vue de test pour vérifier que l'i18n fonctionne.
GET /api/i18n-test/?lang=en  → {"language": "en", "message": "Hello", "sample_validation": "Quantity is required for each entry line."}
GET /api/i18n-test/?lang=fr  → {"language": "fr", "message": "Bonjour", ...}
Sans ?lang= : utilise Accept-Language ou défaut fr.
"""
from django.utils.translation import gettext as _
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def i18n_test(request):
    """Retourne la langue active et des chaînes traduites pour vérifier l'i18n."""
    lang = getattr(request, "LANGUAGE_CODE", "fr")
    return Response({
        "language": lang,
        "message": _("Bonjour"),
        "sample_validation": _("La quantité est obligatoire pour chaque ligne d'entrée."),
    })
