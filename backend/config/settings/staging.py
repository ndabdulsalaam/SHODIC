"""
Staging settings for pre-production testing.
"""

from .base import *  # noqa: F401,F403

DJANGO_ENV = "staging"

DEBUG = env_bool("DEBUG")  # noqa: F405

SECRET_KEY = env_value("SECRET_KEY")  # noqa: F405

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")  # noqa: F405

ALLOWED_ORIGINS = env_list("ALLOWED_ORIGINS")  # noqa: F405
CORS_ALLOWED_ORIGINS = ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS

DATABASES = database_config(required=True)  # noqa: F405

QDRANT_COLLECTION = env_value("QDRANT_COLLECTION")  # noqa: F405

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
