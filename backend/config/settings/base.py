"""
Base Django settings shared by dev, staging, and production.
"""

import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]


def env_value(name, allow_blank=False):
    value = os.getenv(name)
    if value is None:
        raise ImproperlyConfigured(f"{name} must be declared in the environment.")
    value = value.strip()
    if not allow_blank and not value:
        raise ImproperlyConfigured(f"{name} must be set for this environment.")
    return value


def env_bool(name):
    value = os.getenv(name)
    if value is None:
        raise ImproperlyConfigured(f"{name} must be declared in the environment.")
    return value.strip().lower() in ("true", "1", "yes", "on")


def env_int(name):
    value = env_value(name)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ImproperlyConfigured(f"{name} must be an integer.") from None


def env_list(name):
    return [
        item.strip()
        for item in env_value(name).split(",")
        if item.strip()
    ]




def database_config(required=False):
    database_url = os.getenv("DATABASE_URL")
    if not required:
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
    if not database_url or not database_url.strip():
        raise ImproperlyConfigured("DATABASE_URL must be declared in the environment.")
    return {
        "default": dj_database_url.parse(
            database_url.strip(),
            conn_max_age=env_int("DATABASE_CONN_MAX_AGE"),
            ssl_require=env_bool("DATABASE_SSL_REQUIRE"),
        )
    }

DJANGO_ENV = env_value("DJANGO_ENV")

SECRET_KEY = env_value("SECRET_KEY")

DEBUG = env_bool("DEBUG")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "django_q",
    # Local
    "fildah",
    "rxchat",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

if "test" in sys.argv:
    STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"
    MIDDLEWARE = [
        middleware
        for middleware in MIDDLEWARE
        if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
    ]

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = False
WHITENOISE_MANIFEST_STRICT = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Browser origins allowed to call the API with session cookies.
ALLOWED_ORIGINS = env_list("ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGINS = ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# Trusted browser origins for cross-site session POSTs.
CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "config.authentication.CsrfExemptSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# LLM Configuration (OpenRouter)
OPENROUTER_API_KEY = env_value("OPENROUTER_API_KEY", allow_blank=True)
OPENROUTER_BACKUP_API_KEY = env_value("OPENROUTER_BACKUP_API_KEY", allow_blank=True)
OPENROUTER_BASE_URL = env_value("OPENROUTER_BASE_URL")
OPENROUTER_TEXT_MODEL = env_value("OPENROUTER_MODEL")
OPENROUTER_VISION_MODEL = env_value("OPENROUTER_VISION_MODEL")
OPENROUTER_VISION_MODEL_FALLBACK = env_value("OPENROUTER_VISION_MODEL_FALLBACK")
OPENROUTER_TEXT_MAX_TOKENS = env_int("OPENROUTER_TEXT_MAX_TOKENS")
OPENROUTER_REASONING_MAX_TOKENS = env_int("OPENROUTER_REASONING_MAX_TOKENS")

# Vector DB - Qdrant Cloud (for RAG retrieval)
QDRANT_URL = env_value("QDRANT_URL", allow_blank=True)
QDRANT_API_KEY = env_value("QDRANT_API_KEY", allow_blank=True)
QDRANT_COLLECTION = env_value("QDRANT_COLLECTION")
QDRANT_INFERENCE_MODEL = env_value("QDRANT_INFERENCE_MODEL")
QDRANT_SPARSE_MODEL = env_value("QDRANT_SPARSE_MODEL")
QDRANT_DENSE_VECTOR_NAME = env_value("QDRANT_DENSE_VECTOR_NAME")
QDRANT_SPARSE_VECTOR_NAME = env_value("QDRANT_SPARSE_VECTOR_NAME")
QDRANT_VECTOR_SIZE = env_int("QDRANT_VECTOR_SIZE")
QDRANT_DISTANCE = env_value("QDRANT_DISTANCE")

# Data acquisition
OPENFDA_API_KEY = env_value("OPENFDA_API_KEY", allow_blank=True)

# Chat attachments are intentionally paused until the frontend upload flow is
# ready to ship again. Existing persisted image previews can still be resent.
RXCHAT_ATTACHMENTS_ENABLED = env_bool("RXCHAT_ATTACHMENTS_ENABLED")

Q_CLUSTER = {
    "name": "rxchat",
    "workers": env_int("Q_CLUSTER_WORKERS"),
    "timeout": env_int("Q_CLUSTER_TIMEOUT"),
    "retry": env_int("Q_CLUSTER_RETRY"),
    "orm": "default",
    "save_limit": 50,
}

# Email - Brevo HTTP API (primary), Django console (dev fallback)
BREVO_API_KEY = env_value("BREVO_API_KEY", allow_blank=True)
BREVO_SENDER_EMAIL = env_value("BREVO_SENDER_EMAIL", allow_blank=True)
BREVO_SENDER_NAME_DEFAULT = env_value("BREVO_SENDER_NAME_DEFAULT")
BREVO_SENDER_NAME_RXCHAT = env_value("BREVO_SENDER_NAME_RXCHAT")


# Django email backend (used as fallback when BREVO_API_KEY is not set)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = (
    f"{BREVO_SENDER_NAME_RXCHAT} <{BREVO_SENDER_EMAIL}>"
    if BREVO_SENDER_EMAIL
    else env_value("DEFAULT_FROM_EMAIL")
)

# Google OAuth
GOOGLE_CLIENT_ID = env_value("GOOGLE_CLIENT_ID", allow_blank=True)
GOOGLE_CLIENT_SECRET = env_value("GOOGLE_CLIENT_SECRET", allow_blank=True)

# Session - 30-day sliding session to match trusted device window
SESSION_COOKIE_AGE = 30 * 24 * 60 * 60
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
