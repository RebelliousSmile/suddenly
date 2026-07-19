"""A CHARACTER_APPEARS marker records a durable CharacterAppearance.

Covers the service bridge (``record_appearance_from_marker``) and its wiring
into the ``marker_create`` view.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import AppearanceRole, CharacterAppearance
from suddenly.games.models import (
    MarkerKind,
    Rapport,
    RapportKind,
    RapportMarker,
)
from suddenly.games.services import record_appearance_from_marker
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _rapport_and_character(user: object) -> tuple[Rapport, object]:
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    rapport = Rapport.objects.create(report=report, kind=RapportKind.ACTION, content="An action.")
    character = CharacterFactory(origin_game=game, creator=user)
    return rapport, character


# ---------------------------------------------------------------------------
# Service — record_appearance_from_marker
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_character_appears_records_appearance() -> None:
    """A CHARACTER_APPEARS marker creates a CharacterAppearance for the scene."""
    user = UserFactory()
    rapport, character = _rapport_and_character(user)
    marker = RapportMarker.objects.create(
        rapport=rapport, kind=MarkerKind.CHARACTER_APPEARS, character=character
    )

    appearance = record_appearance_from_marker(marker)

    assert appearance is not None
    assert appearance.character == character
    assert appearance.report == rapport.report
    assert appearance.role == AppearanceRole.SUPPORTING


@pytest.mark.django_db
def test_character_leaves_records_no_appearance() -> None:
    """CHARACTER_LEAVES does not create an appearance — presence is durable."""
    user = UserFactory()
    rapport, character = _rapport_and_character(user)
    marker = RapportMarker.objects.create(
        rapport=rapport, kind=MarkerKind.CHARACTER_LEAVES, character=character
    )

    assert record_appearance_from_marker(marker) is None
    assert not CharacterAppearance.objects.filter(report=rapport.report).exists()


@pytest.mark.django_db
def test_start_marker_records_no_appearance() -> None:
    """A non-character marker (START) never touches appearances."""
    user = UserFactory()
    rapport, _character = _rapport_and_character(user)
    marker = RapportMarker.objects.create(rapport=rapport, kind=MarkerKind.START)

    assert record_appearance_from_marker(marker) is None
    assert not CharacterAppearance.objects.filter(report=rapport.report).exists()


@pytest.mark.django_db
def test_appearance_is_idempotent_and_preserves_role() -> None:
    """An existing appearance (e.g. MAIN) is left untouched and not duplicated."""
    user = UserFactory()
    rapport, character = _rapport_and_character(user)
    CharacterAppearance.objects.create(
        character=character, report=rapport.report, role=AppearanceRole.MAIN
    )
    marker = RapportMarker.objects.create(
        rapport=rapport, kind=MarkerKind.CHARACTER_APPEARS, character=character
    )

    appearance = record_appearance_from_marker(marker)

    assert appearance is not None
    assert appearance.role == AppearanceRole.MAIN
    assert (
        CharacterAppearance.objects.filter(character=character, report=rapport.report).count() == 1
    )


# ---------------------------------------------------------------------------
# View — marker_create wiring
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_character_appears_via_view_creates_appearance(client: Client) -> None:
    """POSTing a CHARACTER_APPEARS marker through the view records the appearance."""
    user = UserFactory()
    rapport, character = _rapport_and_character(user)
    url = reverse(
        "games:marker_create",
        kwargs={
            "game_pk": str(rapport.report.game.pk),
            "pk": str(rapport.report.pk),
            "rapport_pk": str(rapport.pk),
        },
    )

    client.force_login(user)
    response = client.post(
        url, data={"kind": MarkerKind.CHARACTER_APPEARS, "character": str(character.pk)}
    )

    assert response.status_code == 200
    assert CharacterAppearance.objects.filter(character=character, report=rapport.report).exists()
