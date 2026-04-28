"""
Tests for the version and available languages helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from suddenly.core.version import get_available_languages, get_version


class TestGetVersion:
    def setup_method(self) -> None:
        get_version.cache_clear()

    def test_returns_string(self) -> None:
        result = get_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_pyproject_version(self) -> None:
        result = get_version()
        assert result == "0.1.0"

    def test_fallback_on_package_not_found(self) -> None:
        from importlib.metadata import PackageNotFoundError

        with patch("suddenly.core.version.version", side_effect=PackageNotFoundError):
            get_version.cache_clear()
            result = get_version()
        assert result == "0.0.0-dev"


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
