"""
Tests for NodeInfo version and languages fields.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.test import Client

from suddenly.core.version import get_available_languages, get_version


@pytest.mark.django_db
class TestNodeInfoVersion:
    def test_software_version_matches_get_version(self, client: Client) -> None:
        response = client.get("/.well-known/nodeinfo/2.0")
        assert response.status_code == 200
        data = response.json()
        assert data["software"]["version"] == get_version()

    def test_software_version_is_not_hardcoded(self, client: Client) -> None:
        fake_version = "99.99.99"
        with patch("suddenly.core.version.get_version", return_value=fake_version):
            # Re-import to pick up patch inside the view module
            from suddenly.activitypub import views as ap_views

            with patch.object(ap_views, "get_version", return_value=fake_version):
                response = client.get("/.well-known/nodeinfo/2.0")
        assert response.status_code == 200
        data = response.json()
        assert data["software"]["version"] == fake_version

    def test_metadata_languages_matches_get_available_languages(self, client: Client) -> None:
        response = client.get("/.well-known/nodeinfo/2.0")
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data["metadata"]
        assert data["metadata"]["languages"] == get_available_languages()

    def test_metadata_languages_reflects_available_po_files(
        self, client: Client, tmp_path: Any, settings: Any
    ) -> None:
        for lang in ("en", "fr"):
            lc_dir = tmp_path / "locale" / lang / "LC_MESSAGES"
            lc_dir.mkdir(parents=True)
            (lc_dir / "django.po").write_text("# translation\nmsgid ''\nmsgstr ''\n")
        settings.BASE_DIR = tmp_path
        get_available_languages.cache_clear()
        response = client.get("/.well-known/nodeinfo/2.0")
        data = response.json()
        assert data["metadata"]["languages"] == ["en", "fr"]
        get_available_languages.cache_clear()
