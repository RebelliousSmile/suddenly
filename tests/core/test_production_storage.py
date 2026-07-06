"""
Tests for conditional S3/R2 storage backend selection in production settings.

config.settings.production is never loaded by the default test settings
(config.settings.development) — it's tested here by importing/reloading the
module directly with monkeypatched env vars. Reloading only rebuilds the
plain-Python attributes of the `production` module object; it does not touch
the active `django.conf.settings` (still `development`). This is safe as long
as the override rebinds STORAGES to a new dict rather than mutating the
shared `base.STORAGES` object.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

REQUIRED_ENV = {
    "SECRET_KEY": "test-secret-key",
    "DOMAIN": "example.com",
    "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
}


def _reload_production(monkeypatch: pytest.MonkeyPatch, extra_env: dict[str, str]) -> Any:
    for key, value in {**REQUIRED_ENV, **extra_env}.items():
        monkeypatch.setenv(key, value)

    from config.settings import production

    return importlib.reload(production)


@pytest.fixture(autouse=True)
def _reset_production_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Reload config.settings.production back to its filesystem-default state.

    importlib.reload() rebinds the module object in sys.modules; monkeypatch
    reverting env vars after a test does NOT re-run the module, so whatever
    state the last reload left it in (e.g. S3-configured STORAGES) would leak
    into any later test/module that imports config.settings.production,
    regardless of the order in which the tests in this file ran. Reloading
    once more with a clean, S3-var-free env in teardown guarantees the module
    is always left in its default state.
    """
    yield

    for key in (
        "AWS_STORAGE_BUCKET_NAME",
        "AWS_S3_ENDPOINT_URL",
        "AWS_S3_REGION_NAME",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    from config.settings import production

    importlib.reload(production)


class TestFilesystemFallback:
    def test_backend_is_filesystem_when_bucket_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AWS_STORAGE_BUCKET_NAME", raising=False)
        production = _reload_production(monkeypatch, {})

        assert (
            production.STORAGES["default"]["BACKEND"]
            == "django.core.files.storage.FileSystemStorage"
        )

    def test_storages_is_not_rebound_when_bucket_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AWS_STORAGE_BUCKET_NAME", raising=False)
        production = _reload_production(monkeypatch, {})

        from config.settings import base

        assert production.STORAGES is base.STORAGES


class TestS3Backend:
    def test_backend_is_s3_when_bucket_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        production = _reload_production(
            monkeypatch,
            {
                "AWS_STORAGE_BUCKET_NAME": "test-bucket",
                "AWS_S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
                "AWS_S3_REGION_NAME": "auto",
                "AWS_ACCESS_KEY_ID": "dummy-key",
                "AWS_SECRET_ACCESS_KEY": "dummy-secret",
            },
        )

        default = production.STORAGES["default"]
        assert default["BACKEND"] == "storages.backends.s3.S3Storage"
        options = default["OPTIONS"]
        assert options["bucket_name"] == "test-bucket"
        assert options["querystring_auth"] is False
        assert options["file_overwrite"] is False
        assert "default_acl" not in options

    def test_base_storages_unmutated_after_s3_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _reload_production(
            monkeypatch,
            {
                "AWS_STORAGE_BUCKET_NAME": "test-bucket",
                "AWS_S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
                "AWS_S3_REGION_NAME": "auto",
                "AWS_ACCESS_KEY_ID": "dummy-key",
                "AWS_SECRET_ACCESS_KEY": "dummy-secret",
            },
        )

        from config.settings import base

        assert base.STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage"
