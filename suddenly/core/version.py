"""
Version and available languages helpers.
"""

from __future__ import annotations

import functools
from pathlib import Path

from django.conf import settings

from suddenly import __version__


@functools.cache
def get_version() -> str:
    """Return the software version.

    Reads the committed ``suddenly.__version__`` constant (single source of
    truth) at runtime — never ``importlib.metadata`` nor git tags, so a fresh
    ``git pull`` reports the right version without any reinstall or build step.
    Mirrors BookWyrm's ``VERSION`` file and Mastodon's ``version.rb``.
    """
    return __version__


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
