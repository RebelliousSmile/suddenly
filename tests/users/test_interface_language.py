"""
Tests for the interface_language field on User.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.factories import UserFactory


@pytest.mark.django_db
class TestInterfaceLanguageField:
    def test_default_is_empty_string(self) -> None:
        user = UserFactory()
        assert user.interface_language == ""

    def test_content_language_unchanged(self) -> None:
        user = UserFactory(content_language="fr")
        assert user.content_language == "fr"
        assert user.interface_language == ""

    def test_can_set_interface_language(self) -> None:
        user = UserFactory(interface_language="en")
        assert user.interface_language == "en"

    def test_can_set_to_empty(self) -> None:
        user = UserFactory(interface_language="en")
        user.interface_language = ""
        user.save()
        user.refresh_from_db()
        assert user.interface_language == ""

    def test_existing_users_keep_content_language(self, db: Any) -> None:
        user = UserFactory(content_language="fr", interface_language="")
        user.refresh_from_db()
        assert user.content_language == "fr"
        assert user.interface_language == ""
