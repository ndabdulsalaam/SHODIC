"""
Production settings for the live app.
"""

from .base import *  # noqa: F401,F403

DJANGO_ENV = "production"

DEBUG = False

SECRET_KEY = env_required("SECRET_KEY")  # noqa: F405

ALLOWED_HOSTS = env_required_list("ALLOWED_HOSTS")  # noqa: F405

ALLOWED_ORIGINS = env_required_list("ALLOWED_ORIGINS")  # noqa: F405
CORS_ALLOWED_ORIGINS = ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS

DATABASES = database_config(  # noqa: F405
    required=True,
    conn_max_age=600,
    ssl_require=env_bool("DATABASE_SSL_REQUIRE", True),  # noqa: F405
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
