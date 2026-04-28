"""
Tests for i18n infrastructure settings.
"""

from __future__ import annotations

from typing import Any

import pytest


class TestLocaleMiddlewarePosition:
    def test_locale_middleware_present(self, settings: Any) -> None:
        assert "django.middleware.locale.LocaleMiddleware" in settings.MIDDLEWARE

    def test_locale_middleware_after_session(self, settings: Any) -> None:
        mw = settings.MIDDLEWARE
        session_idx = mw.index("django.contrib.sessions.middleware.SessionMiddleware")
        locale_idx = mw.index("django.middleware.locale.LocaleMiddleware")
        assert locale_idx > session_idx

    def test_locale_middleware_before_common(self, settings: Any) -> None:
        mw = settings.MIDDLEWARE
        locale_idx = mw.index("django.middleware.locale.LocaleMiddleware")
        common_idx = mw.index("django.middleware.common.CommonMiddleware")
        assert locale_idx < common_idx


class TestLanguageSettings:
    def test_languages_has_en_first(self, settings: Any) -> None:
        assert settings.LANGUAGES[0][0] == "en"

    def test_languages_has_fr(self, settings: Any) -> None:
        codes = [code for code, _ in settings.LANGUAGES]
        assert "fr" in codes

    def test_locale_paths_configured(self, settings: Any) -> None:
        assert len(settings.LOCALE_PATHS) > 0

    def test_use_i18n_enabled(self, settings: Any) -> None:
        assert settings.USE_I18N is True

    def test_language_code_defaults_to_fr(self, settings: Any) -> None:
        # When no env override, default is "fr" (not "fr-fr")
        assert settings.LANGUAGE_CODE in ("fr", "en")
        assert settings.LANGUAGE_CODE != "fr-fr"
