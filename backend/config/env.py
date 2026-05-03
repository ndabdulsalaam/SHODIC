"""
Branch-aware environment loading for local Django commands.
"""

import os
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_LOADED_FLAG = "FILDAH_ENV_LOADED"

SETTINGS_BY_ENV = {
    "dev": "config.settings.dev",
    "staging": "config.settings.staging",
    "production": "config.settings.production",
}


def current_git_branch():
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=BASE_DIR.parent,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"

    branch = result.stdout.strip()
    return branch or "unknown"


def _env_path(value):
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


def _reject_forbidden_env_file(path):
    if path.name == ".env.old":
        raise ImproperlyConfigured(".env.old is a private recycle bin and cannot be loaded.")
    if path.name == ".env":
        raise ImproperlyConfigured("backend/.env is no longer supported. Use .env.dev or .env.staging.")


def _load_env_file(path):
    _reject_forbidden_env_file(path)
    if not path.exists():
        raise ImproperlyConfigured(f"Environment file not found: {path.name}")
    load_dotenv(path, override=False)


def _env_file_for_branch(branch):
    if branch == "dev":
        return BASE_DIR / ".env.dev"
    if branch == "staging":
        return BASE_DIR / ".env.staging"
    if branch == "main":
        raise ImproperlyConfigured(
            "Refusing to run locally from main. Merge dev -> staging -> main, "
            "and run production only with host-managed environment variables."
        )
    return BASE_DIR / ".env.dev"


def _settings_module_for_env(env_name):
    return SETTINGS_BY_ENV.get(env_name, SETTINGS_BY_ENV["dev"])


def _report_environment(branch):
    if os.getenv("FILDAH_ENV_REPORT_PRINTED"):
        return
    os.environ["FILDAH_ENV_REPORT_PRINTED"] = "1"
    env_name = os.getenv("DJANGO_ENV", "").strip().lower() or "undeclared"
    print(f"Fildah environment: branch={branch}, django_env={env_name}", file=sys.stderr)


def configure_environment():
    """
    Load local env variables once and align DJANGO_SETTINGS_MODULE with DJANGO_ENV.

    Production is intentionally different: when DJANGO_ENV=production is already
    present, local env files are skipped so the host platform is the source of
    truth.
    """
    branch = current_git_branch()

    if os.getenv(ENV_LOADED_FLAG):
        _report_environment(branch)
        return

    os.environ[ENV_LOADED_FLAG] = "1"

    existing_env = os.getenv("DJANGO_ENV", "").strip().lower()
    if existing_env == "production":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", SETTINGS_BY_ENV["production"])
        _report_environment(branch)
        return

    explicit_env_file = os.getenv("ENV_FILE", "").strip()
    if explicit_env_file:
        _load_env_file(_env_path(explicit_env_file))
    else:
        _load_env_file(_env_file_for_branch(branch))

    env_name = os.getenv("DJANGO_ENV", "").strip().lower()
    if not env_name:
        raise ImproperlyConfigured("DJANGO_ENV must be declared in the selected environment.")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", _settings_module_for_env(env_name))
    _report_environment(branch)
