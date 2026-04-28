"""
Tests for i18n — PO file integrity and locale-switching rendering.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client, override_settings

LOCALE_DIR = Path(__file__).resolve().parents[2] / "locale"


class TestLocaleFilesExist:
    def test_fr_po_exists(self) -> None:
        assert (LOCALE_DIR / "fr" / "LC_MESSAGES" / "django.po").exists()

    def test_en_po_exists(self) -> None:
        assert (LOCALE_DIR / "en" / "LC_MESSAGES" / "django.po").exists()

    def test_fr_mo_exists(self) -> None:
        assert (LOCALE_DIR / "fr" / "LC_MESSAGES" / "django.mo").exists()

    def test_en_mo_exists(self) -> None:
        assert (LOCALE_DIR / "en" / "LC_MESSAGES" / "django.mo").exists()


class TestNoFuzzyTranslations:
    def _parse_entries(self, po_path: Path) -> list[dict]:
        """Parse a .po file into a list of entry dicts with flags, msgid, msgstr."""
        entries = []
        current: dict = {}
        for line in po_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#, "):
                current.setdefault("flags", []).extend(f.strip() for f in line[3:].split(","))
            elif line.startswith("msgid "):
                current["msgid"] = line[7:-1]  # strip quotes
            elif line.startswith("msgstr "):
                current["msgstr"] = line[8:-1]  # strip quotes
                entries.append(current)
                current = {}
        return entries

    def test_no_fuzzy_in_fr_po(self) -> None:
        po_path = LOCALE_DIR / "fr" / "LC_MESSAGES" / "django.po"
        entries = self._parse_entries(po_path)
        fuzzy_entries = [e for e in entries if "fuzzy" in e.get("flags", [])]
        assert fuzzy_entries == [], (
            f"Found {len(fuzzy_entries)} fuzzy entries in fr.po: "
            + ", ".join(repr(e["msgid"]) for e in fuzzy_entries[:5])
        )

    def test_no_empty_msgstr_in_fr_po(self) -> None:
        po_path = LOCALE_DIR / "fr" / "LC_MESSAGES" / "django.po"
        entries = self._parse_entries(po_path)
        # Skip header entry (msgid == "")
        missing = [e for e in entries if e.get("msgid", "") != "" and e.get("msgstr", "") == ""]
        assert missing == [], f"Found {len(missing)} untranslated entries in fr.po: " + ", ".join(
            repr(e["msgid"]) for e in missing[:5]
        )


@pytest.mark.django_db
class TestHomepageLocale:
    def test_homepage_renders_in_english(self) -> None:
        client = Client(HTTP_ACCEPT_LANGUAGE="en")
        with override_settings(LANGUAGE_CODE="en"):
            response = client.get("/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Welcome" in content or "suddenly" in content.lower()

    def test_homepage_renders_in_french(self) -> None:
        client = Client(HTTP_ACCEPT_LANGUAGE="fr")
        with override_settings(LANGUAGE_CODE="fr"):
            response = client.get("/")
        assert response.status_code == 200
        content = response.content.decode()
        # The French translation for "Welcome to" is "Bienvenue sur"
        assert "Bienvenue" in content or "personnages" in content or "joueurs" in content
