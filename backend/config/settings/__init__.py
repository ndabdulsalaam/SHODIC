"""
Environment-aware Django settings package.

Use one of these explicit modules in real environments:

- config.settings.dev
- config.settings.staging
- config.settings.production

This package reads ``DJANGO_ENV`` for backward compatibility with old commands
that still reference ``config.settings`` directly.
"""

import os

_django_env = os.getenv("DJANGO_ENV", "dev").strip().lower()

if _django_env == "production":
    from .production import *  # noqa: F401,F403
elif _django_env == "staging":
    from .staging import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
