"""Pre-commit check: no fuzzy or untranslated entries in fr.po."""

from __future__ import annotations

import sys
from pathlib import Path

PO_PATH = Path("locale/fr/LC_MESSAGES/django.po")


def check(po_path: Path) -> list[str]:
    text = po_path.read_text(encoding="utf-8")
    errors: list[str] = []

    if "#, fuzzy" in text:
        count = text.count("#, fuzzy")
        errors.append(f"{count} fuzzy entry/entries found — run make i18n-check and fix them")

    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("msgid ") or line == 'msgid ""':
            continue
        msgid = line[7:-1]
        for j in range(i + 1, min(i + 5, len(lines))):
            if lines[j].startswith('msgstr ""'):
                errors.append(f"empty msgstr for: {msgid!r}")
                break
            if lines[j].startswith("msgstr "):
                break

    return errors


if __name__ == "__main__":
    if not PO_PATH.exists():
        print(f"WARNING: {PO_PATH} not found, skipping check")
        sys.exit(0)

    errors = check(PO_PATH)
    if errors:
        print("ERROR in fr.po:")
        for e in errors[:10]:
            print(" -", e)
        sys.exit(1)

    print("OK — fr.po has no fuzzy or untranslated entries")
