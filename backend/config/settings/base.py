"""
Base Django settings shared by dev, staging, and production.
"""

import importlib.util
import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

# Load backend/.env when present. Host-provided environment variables still win.
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_list(name, default):
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


def env_required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set for this environment.")
    return value


def env_required_list(name):
    values = env_list(name, "")
    if not values:
        raise ImproperlyConfigured(
            f"{name} must contain at least one comma-separated value."
        )
    return values


def database_config(required=False, conn_max_age=0, ssl_require=False):
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return {
            "default": dj_database_url.parse(
                database_url,
                conn_max_age=conn_max_age,
                ssl_require=ssl_require,
            )
        }

    if required:
        raise ImproperlyConfigured("DATABASE_URL must be set for this environment.")

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


DJANGO_ENV = os.getenv("DJANGO_ENV", "dev")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-before-shared-use")

DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "")

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
    # Local
    "fildah",
    "rxchat",
    "accounts",
]

if importlib.util.find_spec("django_q"):
    INSTALLED_APPS.append("django_q")

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

DATABASES = database_config(required=False)

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
ALLOWED_ORIGINS = env_list("ALLOWED_ORIGINS", "")
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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BACKUP_API_KEY = os.getenv("OPENROUTER_BACKUP_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_TEXT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
OPENROUTER_VISION_MODEL = os.getenv(
    "OPENROUTER_VISION_MODEL",
    "google/gemma-4-31b-it:free",
)
OPENROUTER_VISION_MODEL_FALLBACK = os.getenv(
    "OPENROUTER_VISION_MODEL_FALLBACK",
    "baidu/qianfan-ocr-fast:free",
)
OPENROUTER_TEXT_MAX_TOKENS = env_int("OPENROUTER_TEXT_MAX_TOKENS", 2048)
OPENROUTER_REASONING_MAX_TOKENS = env_int("OPENROUTER_REASONING_MAX_TOKENS", 4096)

# Vector DB - Qdrant Cloud (for RAG retrieval)
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rxchat")
QDRANT_INFERENCE_MODEL = os.getenv(
    "QDRANT_INFERENCE_MODEL",
    "intfloat/multilingual-e5-small",
)
QDRANT_SPARSE_MODEL = os.getenv("QDRANT_SPARSE_MODEL", "qdrant/bm25")
QDRANT_DENSE_VECTOR_NAME = os.getenv("QDRANT_DENSE_VECTOR_NAME", "dense")
QDRANT_SPARSE_VECTOR_NAME = os.getenv("QDRANT_SPARSE_VECTOR_NAME", "sparse")
QDRANT_VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))
QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "Cosine")

# Data acquisition
OPENFDA_API_KEY = os.getenv("OPENFDA_API_KEY", "")

Q_CLUSTER = {
    "name": "rxchat",
    "workers": 1,
    "timeout": 14400,
    "retry": 14500,
    "orm": "default",
    "save_limit": 50,
}

# Email - Brevo HTTP API (primary), Django console (dev fallback)
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME_RXCHAT = os.getenv(
    "BREVO_SENDER_NAME_RXCHAT",
    os.getenv("BREVO_SENDER_NAME", "RxChat"),
)
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", BREVO_SENDER_NAME_RXCHAT)

# Django email backend (used as fallback when BREVO_API_KEY is not set)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = (
    f"{BREVO_SENDER_NAME_RXCHAT} <{BREVO_SENDER_EMAIL}>"
    if BREVO_SENDER_EMAIL
    else "RxChat <noreply@rxchat.dev>"
)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Session - 15-day session to match trusted device window
SESSION_COOKIE_AGE = 15 * 24 * 60 * 60
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = "Lax"
