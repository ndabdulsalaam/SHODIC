"""
Dev settings for local feature work.
"""

from .base import *  # noqa: F401,F403

DJANGO_ENV = "dev"

DEBUG = env_bool("DEBUG")  # noqa: F405

SECRET_KEY = env_value("SECRET_KEY")  # noqa: F405

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")  # noqa: F405

ALLOWED_ORIGINS = env_list("ALLOWED_ORIGINS")  # noqa: F405
CORS_ALLOWED_ORIGINS = ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS

DATABASES = database_config(required=False)  # noqa: F405

QDRANT_COLLECTION = env_value("QDRANT_COLLECTION")  # noqa: F405
