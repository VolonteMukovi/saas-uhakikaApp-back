from pathlib import Path
import os
from datetime import timedelta

from decouple import config

import dj_database_url


import pymysql
pymysql.install_as_MySQLdb()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-saz6n+tnl=6h)&14$j_mm6nt+fuhias)89#&co=i3sb(tr=25%")

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*").split(",")  # Dev uniquement, limiter en prod

if os.environ.get("COOLIFY_URL"):
    ALLOWED_HOSTS.append("*")

INSTALLED_APPS = [
    "config.apps.ConfigConfig",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",
    "users",  # Nouvelle app pour la gestion des utilisateurs
    "stock",
    "caisse",
    "import_excel",
    "rapports",  # Application pour la génération des rapports
    "order",  # Gestion des marchandises en cours de transport
    "abonnements",  # SaaS : formules, licences, paiements
    "inscription",  # SaaS : inscription et onboarding
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "config.http.correlation.CorrelationIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "config.middleware.AcceptLanguageMiddleware",
    "config.http.versioning.ApiVersionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.http.idempotency.IdempotencyMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "abonnements.middleware.LicenceEntrepriseMiddleware",
    "abonnements.middleware.ControleLicenceEcritureMiddleware",
    "abonnements.middleware.ControleFonctionnalitePlanMiddleware",
    "inscription.middleware.ControleConfigurationMetierMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.http.etag.ETagMiddleware",
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'uhakika-idempotency',
    }
}

IDEMPOTENCY_TTL_SECONDS = config('IDEMPOTENCY_TTL_SECONDS', default=86400, cast=int)
IDEMPOTENCY_LOCK_SECONDS = config('IDEMPOTENCY_LOCK_SECONDS', default=120, cast=int)

# CORS — autoriser les en-têtes HTTP du manifeste CURSOR.md (sinon le navigateur
# n'envoie que OPTIONS et jamais GET/POST : écran vide).
from corsheaders.defaults import default_headers, default_methods

CORS_ALLOW_ALL_ORIGINS = True  # Dev, à limiter en prod
CORS_ALLOW_METHODS = list(default_methods)
CORS_ALLOW_HEADERS = (
    *default_headers,
    'if-match',
    'if-none-match',
    'idempotency-key',
    'x-correlation-id',
    'accept-language',
)
CORS_EXPOSE_HEADERS = (
    'etag',
    'x-correlation-id',
    'api-version',
    'idempotency-replayed',
    'content-language',
)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def _mysql_connection_options():
    """
    Options communes MySQL / MariaDB (PyMySQL installé comme MySQLdb).
    - utf8mb4 : même jeu que les migrations Django (défaut moderne), indépendant
      du charset « serveur » affiché par phpMyAdmin (souvent latin1 en meta).
    - sql_mode STRICT_TRANS_TABLES : aligné sur les attentes Django / intégrité.
    """
    opts = {
        "charset": "utf8mb4",
        "init_command": (
            "SET sql_mode='STRICT_TRANS_TABLES', "
            "NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
        ),
    }
    ssl_ca = config("DATABASE_SSL_CA", default="").strip()
    if ssl_ca:
        opts["ssl"] = {"ca": ssl_ca}
    return opts


_CONN_MAX_AGE = config("DATABASE_CONN_MAX_AGE", default=0, cast=int)
_DATABASE_URL = config("DATABASE_URL", default="").strip()

if _DATABASE_URL:
    _parse_kwargs = {"conn_max_age": _CONN_MAX_AGE}
    if _CONN_MAX_AGE > 0:
        _parse_kwargs["conn_health_checks"] = True
    DATABASES = {
        "default": dj_database_url.parse(_DATABASE_URL, **_parse_kwargs),
    }
    _engine = DATABASES["default"].get("ENGINE", "")
    if "mysql" in _engine:
        DATABASES["default"].setdefault("OPTIONS", {})
        DATABASES["default"]["OPTIONS"].update(_mysql_connection_options())
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": config("DATABASE_NAME"),
            "USER": config("DATABASE_USER"),
            "PASSWORD": config("DATABASE_PASSWORD"),
            "HOST": config("DATABASE_HOST", default="localhost"),
            "PORT": config("DATABASE_PORT", default="3306"),
            "CONN_MAX_AGE": _CONN_MAX_AGE,
            "OPTIONS": _mysql_connection_options(),
        }
    }
    if _CONN_MAX_AGE > 0:
        DATABASES["default"]["CONN_HEALTH_CHECKS"] = True


AUTH_USER_MODEL = 'users.User'
    
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'users.authentication.JWTAuthenticationWithContext',
    ),
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.UhakikaPagination',
    'PAGE_SIZE': 25,
    'EXCEPTION_HANDLER': 'config.exception_handlers.exception_handler',
    # 'DEFAULT_PERMISSION_CLASSES': (
    #     'rest_framework.permissions.IsAuthenticated',
    # ),
}

# Configuration JWT : session sécurisée (expiration à 48 h)
SIMPLE_JWT = {
    # Validité des tokens : 48 heures (access + refresh)
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=48),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=48),

    # Rotation : nouveau refresh à chaque refresh (sliding) ; ancien blacklisté
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 30,

    'AUTH_HEADER_TYPES': ('Bearer',),

    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',
}

# Swagger UI / ReDoc (drf-yasg)
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT : valeur `Bearer <access_token>` (obtenu via POST /api/auth/).',
        }
    },
    'USE_SESSION_AUTH': False,
    'DOC_EXPANSION': 'list',
    'OPERATIONS_SORTER': 'alpha',
    'TAGS_SORTER': 'alpha',
    'DISPLAY_OPERATION_ID': True,
    'PERSIST_AUTH': True,
}

REDOC_SETTINGS = {
    'lazyRendering': True,
    'hideDownloadButton': False,
    'expandResponses': '200,201',
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Langues supportées (aligné avec le frontend : fr, en)
LANGUAGES = [
    ("fr", "Français"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
SUPPORTED_LANG_CODES = ["fr", "en"]
DEFAULT_LANG_FOR_API = "fr"

STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === E-mail transactionnel (Brevo SMTP) ===
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="UhakikaApp <noreply@uhakikaapp.store>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_TRANSACTIONAL_FROM = config("EMAIL_TRANSACTIONAL_FROM", default="").strip()

FRONTEND_BASE_URL = config("FRONTEND_BASE_URL", default="http://localhost:5173").rstrip("/")
# Préfixe i18n du frontend Next.js (ex. /fr → /fr/verify-email)
FRONTEND_LOCALE_PREFIX = config("FRONTEND_LOCALE_PREFIX", default="/fr").rstrip("/")
FRONTEND_VERIFY_EMAIL_PATH = config("FRONTEND_VERIFY_EMAIL_PATH", default="/verify-email")
FRONTEND_DASHBOARD_PATH = config("FRONTEND_DASHBOARD_PATH", default="/dashboard")
# URL publique de l'API (lien du bouton e-mail → redirection vers le frontend avec ?token=)
PUBLIC_API_BASE_URL = config("PUBLIC_API_BASE_URL", default="http://127.0.0.1:8000").rstrip("/")
EMAIL_VERIFICATION_LINK_VIA_API = config("EMAIL_VERIFICATION_LINK_VIA_API", default=True, cast=bool)
SUPPORT_EMAIL = config("SUPPORT_EMAIL", default="support@uhakikaapp.store")
# Legacy Resend sandbox (ignoré avec Brevo) — onboarding@resend.dev uniquement
RESEND_SANDBOX_OWNER_EMAIL = config("RESEND_SANDBOX_OWNER_EMAIL", default="").strip().lower()

EMAIL_VERIFICATION_TOKEN_HOURS = config("EMAIL_VERIFICATION_TOKEN_HOURS", default=24, cast=int)
EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = config("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", default=60, cast=int)
EMAIL_VERIFICATION_RESEND_MAX_PER_HOUR = config("EMAIL_VERIFICATION_RESEND_MAX_PER_HOUR", default=5, cast=int)

# === POS / ESC-POS (imprimante ticket 58mm) ===
# Exemple Windows: POS_PRINTER_PORT=COM3
# Exemple Linux:   POS_PRINTER_PORT=/dev/ttyUSB0
POS_PRINTER_BACKEND = config("POS_PRINTER_BACKEND", default="serial").strip().lower()
POS_PRINTER_PORT = config("POS_PRINTER_PORT", default="").strip() or None
POS_PRINTER_NAME = config("POS_PRINTER_NAME", default="").strip()
POS_PRINTER_BAUDRATE = config("POS_PRINTER_BAUDRATE", default=9600, cast=int)
POS_PRINTER_BYTESIZE = config("POS_PRINTER_BYTESIZE", default=8, cast=int)
POS_PRINTER_PARITY = config("POS_PRINTER_PARITY", default="N")
POS_PRINTER_STOPBITS = config("POS_PRINTER_STOPBITS", default=1, cast=int)
POS_PRINTER_TIMEOUT = config("POS_PRINTER_TIMEOUT", default=1, cast=int)
# Largeur texte (caractères/ligne). 58mm = souvent 32 (font A) ou 42 (font B).
POS_PRINTER_CHARS_PER_LINE = config("POS_PRINTER_CHARS_PER_LINE", default=32, cast=int)

# Configuration du logging pour tracer les suppressions automatiques d'articles
# Créer le répertoire logs s'il n'existe pas
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Configuration différente selon l'environnement
LOG_FILE_PATH = LOGS_DIR / 'stock_suppressions.log'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation_id': {
            '()': 'config.http.correlation.CorrelationIdFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{correlation_id}] {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} [{correlation_id}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['correlation_id'],
        },
    },
    'loggers': {
        'stock.views': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Ajouter le handler de fichier seulement si on peut écrire dans le répertoire
try:
    # Test si on peut écrire dans le répertoire
    test_file = LOG_FILE_PATH.parent / 'test_write.tmp'
    test_file.touch()
    test_file.unlink()
    
    # Si le test réussit, ajouter le handler de fichier
    LOGGING['handlers']['file_stock'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': str(LOG_FILE_PATH),
        'formatter': 'verbose',
    }
    LOGGING['loggers']['stock.views']['handlers'] = ['file_stock', 'console']
except (OSError, PermissionError):
    # En production ou si pas de permissions d'écriture, utiliser seulement la console
    pass

# --- Connexion Google OAuth (SaaS / inscription) ---
# Client ID(s) OAuth 2.0 depuis Google Cloud Console (type « Application Web »).
# Plusieurs IDs séparés par des virgules (ex. web + Android).
GOOGLE_OAUTH_CLIENT_IDS = [
    x.strip()
    for x in config('GOOGLE_OAUTH_CLIENT_ID', default='').split(',')
    if x.strip()
]
# Tolérance horloge locale (secondes) pour exp/iat ; fallback tokeninfo si échec horloge.
GOOGLE_OAUTH_CLOCK_SKEW_SECONDS = config('GOOGLE_OAUTH_CLOCK_SKEW_SECONDS', default=300, cast=int)

# --- Contrôle licence SaaS (étape 3) ---
LICENCE_CONTROLE_ACTIF = config('LICENCE_CONTROLE_ACTIF', default=True, cast=bool)

# --- Paiements en ligne (étape 5) ---
PAIEMENT_GATEWAY_SANDBOX = config('PAIEMENT_GATEWAY_SANDBOX', default=DEBUG, cast=bool)
PAIEMENT_RETURN_BASE_URL = config('PAIEMENT_RETURN_BASE_URL', default='https://uhakikaapp.store')
PAIEMENT_WEBHOOK_BASE_URL = config('PAIEMENT_WEBHOOK_BASE_URL', default='http://127.0.0.1:8000')

MAISHA_PAY_API_KEY = config('MAISHA_PAY_API_KEY', default='')
MAISHA_PAY_WEBHOOK_SECRET = config('MAISHA_PAY_WEBHOOK_SECRET', default='')

FLEXPAY_API_KEY = config('FLEXPAY_API_KEY', default='')
FLEXPAY_WEBHOOK_SECRET = config('FLEXPAY_WEBHOOK_SECRET', default='')

SERDI_PAY_API_KEY = config('SERDI_PAY_API_KEY', default='')
SERDI_PAY_WEBHOOK_SECRET = config('SERDI_PAY_WEBHOOK_SECRET', default='')



# Configuration indispensable pour les serveurs derrière le proxy Coolify
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')