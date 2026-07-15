"""Builders that turn characters/reports into Muses context payloads.

Shared by the shared-sequence opening (#127) and the claim-coherence analysis
(#128). Kept out of the ``muses`` app on purpose: the client stays model-
agnostic, and everything that knows about Character/Report lives here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Character


def character_sheet(character: Character) -> dict[str, object]:
    """A compact character sheet for the hub — name, blurb, status, axial tags."""
    return {
        "id": str(character.id),
        "name": character.name,
        "description": character.description,
        "status": character.status,
        "tags": axial_tags(character),
    }


def axial_tags(character: Character) -> list[str]:
    """Axial tags derived from the character's origin fiction."""
    return [tag.name for tag in character.tags.all()]


def corpus_content(character: Character, *, limit: int = 5) -> str:
    """A single text corpus for a character: name, blurb, then its anchor reports.

    Used by claim coherence (#128) to hand the hub one labelled body per side.
    """
    parts = [character.name, character.description, *anchor_reports(character, limit=limit)]
    return "\n\n".join(part for part in parts if part)


def anchor_reports(character: Character, *, limit: int = 5) -> list[str]:
    """Text of the reports where the character appears — its anchor scene(s).

    Only published report content, oldest first (the appearance scene comes
    first). Empty bodies are skipped.
    """
    appearances = (
        character.appearances.select_related("report")
        .filter(report__status="published")
        .order_by("report__published_at")[:limit]
    )
    return [a.report.content for a in appearances if a.report.content]
