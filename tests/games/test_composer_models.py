"""Model-level rules for the unified composer (prompt §1).

Covers GameCast (availability), Report.language (BCP-47, no enum), RapportMedia
(OneToOne + description-only) and the Rapport actor rules (§2c) enforced in
``clean``.
"""

from __future__ import annotations

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from suddenly.characters.models import CharacterStatus
from suddenly.games.models import (
    GameCast,
    Rapport,
    RapportKind,
    RapportMedia,
)
from tests.factories import CharacterFactory, GameFactory, ReportFactory


def _png() -> SimpleUploadedFile:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (0, 0, 0)).save(buf, format="PNG")
    return SimpleUploadedFile("x.png", buf.getvalue(), content_type="image/png")


# ---------------------------------------------------------------------------
# GameCast — availability before the first post
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_gamecast_same_character_two_games_same_uuid() -> None:
    """A character born in game A can be cast in game B — same UUID, no dup."""
    a = GameFactory()
    b = GameFactory()
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=a)

    GameCast.objects.create(game=a, character=npc)
    GameCast.objects.create(game=b, character=npc)

    assert npc.castings.count() == 2
    assert set(npc.castings.values_list("game", flat=True)) == {a.pk, b.pk}


@pytest.mark.django_db
def test_gamecast_unique_per_game_character() -> None:
    game = GameFactory()
    npc = CharacterFactory(status=CharacterStatus.NPC, origin_game=game)
    GameCast.objects.create(game=game, character=npc)

    with pytest.raises(IntegrityError):
        GameCast.objects.create(game=game, character=npc)


# ---------------------------------------------------------------------------
# Report.language — BCP-47, no enum
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_report_language_default_fr() -> None:
    report = ReportFactory()
    assert report.language == "fr"


@pytest.mark.django_db
def test_report_language_accepts_bcp47_subtag() -> None:
    report = ReportFactory(language="fr-CA")
    report.full_clean()  # no choices constraint to reject a regional subtag
    report.refresh_from_db()
    assert report.language == "fr-CA"


# ---------------------------------------------------------------------------
# RapportMedia — OneToOne + description-only (§1c / §2e)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_media_second_on_same_description_fails() -> None:
    """OneToOne: a second media on the same description is impossible at the DB."""
    report = ReportFactory()
    rapport = Rapport.objects.create(report=report, kind=RapportKind.DESCRIPTION, content="A hall.")
    RapportMedia.objects.create(rapport=rapport, image=_png())

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RapportMedia.objects.create(rapport=rapport, image=_png())


@pytest.mark.django_db
def test_media_on_non_description_fails_validation() -> None:
    report = ReportFactory()
    rapport = Rapport.objects.create(
        report=report, kind=RapportKind.NARRATION, content="Narration."
    )
    media = RapportMedia(rapport=rapport, image=_png())
    with pytest.raises(ValidationError):
        media.full_clean()


# ---------------------------------------------------------------------------
# Rapport.clean — actor rules by kind (§2c)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rapport_narration_forbids_actor() -> None:
    report = ReportFactory()
    pc = CharacterFactory(status=CharacterStatus.PC)
    rapport = Rapport(report=report, kind=RapportKind.NARRATION, content="x", actor=pc)
    with pytest.raises(ValidationError):
        rapport.clean()


@pytest.mark.django_db
def test_rapport_action_requires_actor() -> None:
    report = ReportFactory()
    rapport = Rapport(report=report, kind=RapportKind.ACTION, content="x")
    with pytest.raises(ValidationError):
        rapport.clean()


@pytest.mark.django_db
def test_rapport_discussion_requires_actor() -> None:
    report = ReportFactory()
    rapport = Rapport(report=report, kind=RapportKind.DISCUSSION, content="x")
    with pytest.raises(ValidationError):
        rapport.clean()


@pytest.mark.django_db
def test_rapport_description_actor_optional() -> None:
    report = ReportFactory()
    # Both forms are valid: no actor (Voix du MJ) …
    Rapport(report=report, kind=RapportKind.DESCRIPTION, content="x").clean()
    # … and with an actor.
    pc = CharacterFactory(status=CharacterStatus.PC)
    Rapport(report=report, kind=RapportKind.DESCRIPTION, content="x", actor=pc).clean()
