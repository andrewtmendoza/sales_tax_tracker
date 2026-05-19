from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
RUNNING_TESTS = os.getenv("DJANGO_SETTINGS_MODULE") == "sales_tax_tracker.test_settings"


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(key, default).split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "receipts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "sales_tax_tracker.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sales_tax_tracker.wsgi.application"
ASGI_APPLICATION = "sales_tax_tracker.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "sales_tax_tracker"),
        "USER": os.getenv("POSTGRES_USER", "salt"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "salt"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Los_Angeles")
USE_I18N = True
USE_TZ = True
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "receipts:dashboard"
LOGOUT_REDIRECT_URL = "login"
CSRF_COOKIE_HTTPONLY = False

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or RUNNING_TESTS
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

RUSTFS_ENDPOINT_URL = os.getenv("RUSTFS_ENDPOINT_URL", "http://localhost:9000")
RUSTFS_PUBLIC_ENDPOINT_URL = os.getenv("RUSTFS_PUBLIC_ENDPOINT_URL", RUSTFS_ENDPOINT_URL)
RUSTFS_ACCESS_KEY = os.getenv("RUSTFS_ACCESS_KEY", "rustfsadmin")
RUSTFS_SECRET_KEY = os.getenv("RUSTFS_SECRET_KEY", "rustfsadmin")
RUSTFS_BUCKET = os.getenv("RUSTFS_BUCKET", "receipts")
RUSTFS_REGION = os.getenv("RUSTFS_REGION", "us-east-1")

RECEIPT_LLM_RESPONSES_URL = os.getenv("RECEIPT_LLM_RESPONSES_URL", "").rstrip("/")
if RECEIPT_LLM_RESPONSES_URL.endswith("/v1"):
    RECEIPT_LLM_RESPONSES_URL = f"{RECEIPT_LLM_RESPONSES_URL}/responses"

RECEIPT_LLM_API_KEY = os.getenv("RECEIPT_LLM_API_KEY", "")
RECEIPT_LLM_MODEL = os.getenv("RECEIPT_LLM_MODEL", "")
RECEIPT_LLM_TIMEOUT_SECONDS = int(os.getenv("RECEIPT_LLM_TIMEOUT_SECONDS", "120"))

RECEIPT_MAX_UPLOAD_BYTES = int(os.getenv("RECEIPT_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
RECEIPT_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}


def validate_runtime_settings() -> None:
    if RUNNING_TESTS:
        return

    errors: list[str] = []

    if not SECRET_KEY or SECRET_KEY == "replace-with-a-long-random-secret":
        errors.append("DJANGO_SECRET_KEY must be set to a real value.")

    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["*"]:
        errors.append("DJANGO_ALLOWED_HOSTS must list the hostnames that serve this app.")

    if not RECEIPT_LLM_RESPONSES_URL:
        errors.append("RECEIPT_LLM_RESPONSES_URL is required.")

    if not RECEIPT_LLM_API_KEY or RECEIPT_LLM_API_KEY == "replace-with-openai-api-key":
        errors.append("RECEIPT_LLM_API_KEY is required.")

    if not RECEIPT_LLM_MODEL:
        errors.append("RECEIPT_LLM_MODEL is required.")

    if errors:
        raise RuntimeError("Invalid runtime configuration:\n- " + "\n- ".join(errors))


validate_runtime_settings()
