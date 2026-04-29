"""
Tests for NodeInfo version and languages fields.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.test import Client

from suddenly.core.models import InstanceSettings
from suddenly.core.version import get_version


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

    def test_metadata_languages_contains_instance_language(self, client: Client) -> None:
        """NodeInfo languages list reflects the active instance language."""
        response = client.get("/.well-known/nodeinfo/2.0")
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data["metadata"]
        instance_lang = InstanceSettings.get().language
        assert data["metadata"]["languages"] == [instance_lang]

    def test_metadata_languages_reflects_instance_settings(
        self, client: Client, settings: Any
    ) -> None:
        """Changing InstanceSettings.language changes the languages list in NodeInfo."""
        instance = InstanceSettings.get()
        # Toggle to the other language
        new_lang = "en" if instance.language == "fr" else "fr"
        instance.language = new_lang
        instance.save()
        response = client.get("/.well-known/nodeinfo/2.0")
        data = response.json()
        assert data["metadata"]["languages"] == [new_lang]
