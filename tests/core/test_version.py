"""
Tests for the version and available languages helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from suddenly import __version__
from suddenly.core.version import get_available_languages, get_version


class TestGetVersion:
    def setup_method(self) -> None:
        get_version.cache_clear()

    def test_returns_string(self) -> None:
        result = get_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_matches_version_constant(self) -> None:
        # Single source of truth: get_version() reflects suddenly.__version__
        # (a committed constant), never package metadata — so it stays correct
        # on a bare git pull, and this test never breaks on a version bump.
        assert get_version() == __version__


class TestGetAvailableLanguages:
    def setup_method(self) -> None:
        get_available_languages.cache_clear()

    def teardown_method(self) -> None:
        get_available_languages.cache_clear()

    def test_returns_list(self) -> None:
        result = get_available_languages()
        assert isinstance(result, list)

    def test_returns_sorted(self) -> None:
        result = get_available_languages()
        assert result == sorted(result)

    def test_empty_when_no_locale_dir(self, tmp_path: Path, settings: Any) -> None:
        settings.BASE_DIR = tmp_path
        get_available_languages.cache_clear()
        result = get_available_languages()
        assert result == []

    def test_detects_po_files(self, tmp_path: Path, settings: Any) -> None:
        for lang in ("en", "fr"):
            lc_dir = tmp_path / "locale" / lang / "LC_MESSAGES"
            lc_dir.mkdir(parents=True)
            (lc_dir / "django.po").write_text("# translation\nmsgid ''\nmsgstr ''\n")
        settings.BASE_DIR = tmp_path
        get_available_languages.cache_clear()
        result = get_available_languages()
        assert result == ["en", "fr"]

    def test_ignores_empty_files(self, tmp_path: Path, settings: Any) -> None:
        lc_dir = tmp_path / "locale" / "es" / "LC_MESSAGES"
        lc_dir.mkdir(parents=True)
        (lc_dir / "django.po").write_text("")
        settings.BASE_DIR = tmp_path
        get_available_languages.cache_clear()
        result = get_available_languages()
        assert "es" not in result
