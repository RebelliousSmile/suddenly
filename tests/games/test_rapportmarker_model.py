"""Tests for RapportMarker model — clean() validation and ordering."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from suddenly.games.models import (
    MarkerKind,
    Rapport,
    RapportKind,
    RapportMarker,
)
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _make_rapport() -> Rapport:
    user = UserFactory()
    game = GameFactory(owner=user)
    report = ReportFactory(game=game, author=user)
    return Rapport.objects.create(report=report, kind=RapportKind.ACTION, content="An action.")


class TestRapportMarkerClean:
    """Unit tests for RapportMarker.clean() — character required/forbidden logic."""

    @pytest.mark.django_db
    def test_character_appears_without_character_raises(self) -> None:
        marker = RapportMarker(kind=MarkerKind.CHARACTER_APPEARS, character=None)
        with pytest.raises(ValidationError) as exc_info:
            marker.clean()
        assert "character" in exc_info.value.message_dict

    @pytest.mark.django_db
    def test_character_appears_with_character_valid(self) -> None:
        character = CharacterFactory()
        marker = RapportMarker(kind=MarkerKind.CHARACTER_APPEARS, character=character)
        marker.clean()  # must not raise

    @pytest.mark.django_db
    def test_start_with_character_raises(self) -> None:
        character = CharacterFactory()
        marker = RapportMarker(kind=MarkerKind.START, character=character)
        with pytest.raises(ValidationError) as exc_info:
            marker.clean()
        assert "character" in exc_info.value.message_dict

    def test_oracle_without_character_valid(self) -> None:
        marker = RapportMarker(kind=MarkerKind.ORACLE, character=None)
        marker.clean()  # must not raise

    def test_end_without_character_valid(self) -> None:
        marker = RapportMarker(kind=MarkerKind.END, character=None)
        marker.clean()  # must not raise


@pytest.mark.django_db
class TestRapportMarkerOrdering:
    """DB tests for RapportMarker ordering."""

    def test_ordering_by_created_at(self) -> None:
        rapport = _make_rapport()

        m1 = RapportMarker.objects.create(rapport=rapport, kind=MarkerKind.START)
        m2 = RapportMarker.objects.create(rapport=rapport, kind=MarkerKind.ORACLE)
        m3 = RapportMarker.objects.create(rapport=rapport, kind=MarkerKind.END)

        qs = list(RapportMarker.objects.filter(rapport=rapport))
        assert qs[0].pk == m1.pk
        assert qs[1].pk == m2.pk
        assert qs[2].pk == m3.pk
