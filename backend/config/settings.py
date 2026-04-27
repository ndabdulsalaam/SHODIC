"""
Django settings for RxChat.
"""

import os
import importlib.util
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_list(name, default):
    return [
        item.strip()
        for item in os.getenv(name, default).split(',')
        if item.strip()
    ]


SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ' ')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'corsheaders',
    # Local
    'fildah',
    'rxchat',
    'accounts',
]

if importlib.util.find_spec('django_q'):
    INSTALLED_APPS.append('django_q')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database — SQLite for dev, PostgreSQL for production
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = False
WHITENOISE_MANIFEST_STRICT = False

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Browser origins allowed to call the API with session cookies.
ALLOWED_ORIGINS = env_list('ALLOWED_ORIGINS', ' ')
CORS_ALLOWED_ORIGINS = ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# Trusted browser origins for cross-site session POSTs.
CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'config.authentication.CsrfExemptSessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# ── LLM Configuration (OpenRouter) ──────────────────────────────────
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_BACKUP_API_KEY = os.getenv('OPENROUTER_BACKUP_API_KEY', '')
OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
OPENROUTER_TEXT_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-120b:free')
OPENROUTER_VISION_MODEL = os.getenv('OPENROUTER_VISION_MODEL', 'google/gemma-4-31b-it:free')
OPENROUTER_VISION_MODEL_FALLBACK = os.getenv('OPENROUTER_VISION_MODEL_FALLBACK', 'baidu/qianfan-ocr-fast:free')
OPENROUTER_TEXT_MAX_TOKENS = env_int('OPENROUTER_TEXT_MAX_TOKENS', 2048)
OPENROUTER_REASONING_MAX_TOKENS = env_int('OPENROUTER_REASONING_MAX_TOKENS', 4096)

# Vector DB — Qdrant Cloud (for RAG retrieval)
QDRANT_URL = os.getenv('QDRANT_URL', '')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', '')
QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'rxchat')
QDRANT_INFERENCE_MODEL = os.getenv('QDRANT_INFERENCE_MODEL', 'intfloat/multilingual-e5-small')
QDRANT_SPARSE_MODEL = os.getenv('QDRANT_SPARSE_MODEL', 'qdrant/bm25')
QDRANT_DENSE_VECTOR_NAME = os.getenv('QDRANT_DENSE_VECTOR_NAME', 'dense')
QDRANT_SPARSE_VECTOR_NAME = os.getenv('QDRANT_SPARSE_VECTOR_NAME', 'sparse')
QDRANT_VECTOR_SIZE = int(os.getenv('QDRANT_VECTOR_SIZE', '384'))
QDRANT_DISTANCE = os.getenv('QDRANT_DISTANCE', 'Cosine')

# Data acquisition
OPENFDA_API_KEY = os.getenv('OPENFDA_API_KEY', '')

Q_CLUSTER = {
    'name': 'rxchat',
    'workers': 1,
    'timeout': 14400,
    'retry': 14500,
    'orm': 'default',
    'save_limit': 50,
}

# Email — Brevo HTTP API (primary), Django console (dev fallback)
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
BREVO_SENDER_EMAIL = os.getenv('BREVO_SENDER_EMAIL', '')
BREVO_SENDER_NAME_RXCHAT = os.getenv(
    'BREVO_SENDER_NAME_RXCHAT',
    os.getenv('BREVO_SENDER_NAME', 'RxChat'),
)
BREVO_SENDER_NAME = os.getenv('BREVO_SENDER_NAME', BREVO_SENDER_NAME_RXCHAT)

# Django email backend (used as fallback when BREVO_API_KEY is not set)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = (
    f'{BREVO_SENDER_NAME_RXCHAT} <{BREVO_SENDER_EMAIL}>'
    if BREVO_SENDER_EMAIL
    else 'RxChat <noreply@rxchat.dev>'
)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

# Session — 15-day session to match trusted device window
SESSION_COOKIE_AGE = 15 * 24 * 60 * 60  # 15 days in seconds

# --- Production deployment (Render) ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'None'
