"""
Dev settings for local feature work.
"""

from .base import *  # noqa: F401,F403

DJANGO_ENV = "dev"

DEBUG = env_bool("DEBUG", True)  # noqa: F405

SECRET_KEY = os.getenv(  # noqa: F405
    "SECRET_KEY",
    "django-insecure-dev-key-change-before-shared-use",
)

ALLOWED_HOSTS = env_list(  # noqa: F405
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,[::1]",
)

ALLOWED_ORIGINS = env_list(  # noqa: F405
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
)
CORS_ALLOWED_ORIGINS = ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS
