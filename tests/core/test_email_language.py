"""
Tests for SuddenlyAccountAdapter — emails always sent in instance language.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from suddenly.users.adapters import SuddenlyAccountAdapter


class TestSuddenlyAccountAdapter:
    def test_send_mail_uses_instance_language(self, settings: Any) -> None:
        settings.LANGUAGE_CODE = "fr"

        adapter = SuddenlyAccountAdapter()
        captured_lang: list[str] = []

        def fake_send_mail(self: Any, template_prefix: str, email: str, context: dict) -> None:
            from django.utils import translation
            captured_lang.append(translation.get_language())

        with patch.object(adapter.__class__.__bases__[0], "send_mail", fake_send_mail):
            adapter.send_mail("account/email/email_confirmation", "user@example.com", {})

        assert captured_lang == ["fr"]

    def test_send_mail_ignores_user_interface_language(self, settings: Any) -> None:
        """Even if the user's interface language is 'en', emails go out in instance language."""
        settings.LANGUAGE_CODE = "fr"

        from django.utils import translation
        translation.activate("en")  # simulate user's interface_language="en"

        adapter = SuddenlyAccountAdapter()
        captured_lang: list[str] = []

        def fake_send_mail(self: Any, template_prefix: str, email: str, context: dict) -> None:
            captured_lang.append(translation.get_language())

        with patch.object(adapter.__class__.__bases__[0], "send_mail", fake_send_mail):
            adapter.send_mail("account/email/password_reset", "user@example.com", {})

        assert captured_lang == ["fr"]
        translation.deactivate()

    def test_send_mail_restores_language_after_call(self, settings: Any) -> None:
        """translation.override must not permanently change the thread's active language."""
        settings.LANGUAGE_CODE = "fr"

        from django.utils import translation
        translation.activate("en")

        adapter = SuddenlyAccountAdapter()

        with patch.object(adapter.__class__.__bases__[0], "send_mail", lambda *a, **kw: None):
            adapter.send_mail("prefix", "e@e.com", {})

        assert translation.get_language() == "en"
        translation.deactivate()
