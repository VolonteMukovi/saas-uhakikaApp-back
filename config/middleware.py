"""
Middleware d'internationalisation pour l'API.

Lit l'en-tête Accept-Language (envoyé par le frontend) et active la langue
correspondante pour la durée de la requête. Seules les langues supportées (fr, en)
sont utilisées ; sinon on retombe sur la langue par défaut (fr).
"""
from django.utils import translation
from django.conf import settings


class AcceptLanguageMiddleware:
    """
    Active la langue de la requête à partir de l'en-tête Accept-Language.
    Aligné avec le frontend qui envoie Accept-Language: fr ou Accept-Language: en.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = self._get_lang_from_request(request)
        translation.activate(lang)
        request.LANGUAGE_CODE = lang
        response = self.get_response(request)
        response["Content-Language"] = lang
        translation.deactivate()
        return response

    def _get_lang_from_request(self, request):
        supported = getattr(settings, "SUPPORTED_LANG_CODES", ["fr", "en"])
        default = getattr(settings, "DEFAULT_LANG_FOR_API", "fr")
        # 1) Paramètre ?lang=en ou ?lang=fr (prioritaire, utile pour tests et clients sans header)
        lang_param = (request.GET.get("lang") or "").strip().lower()
        if lang_param in supported:
            return lang_param
        # 2) En-tête Accept-Language
        accepted = request.META.get("HTTP_ACCEPT_LANGUAGE") or ""
        for part in accepted.split(","):
            part = part.strip().split(";")[0].strip()
            code = part.split("-")[0].lower() if part else ""
            if code in supported:
                return code
        return default
