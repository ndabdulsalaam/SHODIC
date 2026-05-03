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

from config.env import configure_environment

configure_environment()

_django_env = os.getenv("DJANGO_ENV", "").strip().lower()
if not _django_env:
    raise RuntimeError("DJANGO_ENV must be declared before loading Django settings.")

if _django_env == "production":
    from .production import *  # noqa: F401,F403
elif _django_env == "staging":
    from .staging import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
