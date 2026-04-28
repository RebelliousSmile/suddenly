"""
Version and available languages helpers.
"""

from __future__ import annotations

import functools
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from django.conf import settings


@functools.cache
def get_version() -> str:
    try:
        return version("suddenly")
    except PackageNotFoundError:
        return "0.0.0-dev"


@functools.cache
def get_available_languages() -> list[str]:
    locale_dir = Path(settings.BASE_DIR) / "locale"
    if not locale_dir.exists():
        return []
    langs = []
    for lang_dir in locale_dir.iterdir():
        if not lang_dir.is_dir():
            continue
        mo_file = lang_dir / "LC_MESSAGES" / "django.mo"
        po_file = lang_dir / "LC_MESSAGES" / "django.po"
        if (mo_file.exists() and mo_file.stat().st_size > 0) or (
            po_file.exists() and po_file.stat().st_size > 0
        ):
            langs.append(lang_dir.name)
    return sorted(langs)
