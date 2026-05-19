from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "sales_tax_tracker" / "settings.py"


def load_project_settings(monkeypatch, **env_values):
    for key in (
        "DJANGO_SETTINGS_MODULE",
        "DJANGO_TRUST_X_FORWARDED_PROTO",
        "DJANGO_SESSION_COOKIE_SECURE",
        "DJANGO_CSRF_COOKIE_SECURE",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "sales_tax_tracker.test_settings")
    for key, value in env_values.items():
        monkeypatch.setenv(key, value)

    module_name = "_test_project_settings"
    spec = importlib.util.spec_from_file_location(module_name, SETTINGS_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(module_name, None)


def test_proxy_security_settings_default_to_off(monkeypatch):
    project_settings = load_project_settings(monkeypatch)

    assert project_settings.SECURE_PROXY_SSL_HEADER is None
    assert project_settings.SESSION_COOKIE_SECURE is False
    assert project_settings.CSRF_COOKIE_SECURE is False


def test_proxy_security_settings_can_be_enabled(monkeypatch):
    project_settings = load_project_settings(
        monkeypatch,
        DJANGO_TRUST_X_FORWARDED_PROTO="true",
        DJANGO_SESSION_COOKIE_SECURE="true",
        DJANGO_CSRF_COOKIE_SECURE="true",
    )

    assert project_settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert project_settings.SESSION_COOKIE_SECURE is True
    assert project_settings.CSRF_COOKIE_SECURE is True
