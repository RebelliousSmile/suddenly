"""Tests for Rapport model — clean() validation and ordering."""

from __future__ import annotations

import pytest

from suddenly.games.models import Rapport, RapportKind
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


class TestRapportClean:
    """Unit tests for Rapport.clean() — in-memory where possible, DB where a real FK is needed."""

    def test_discussion_requires_actor(self) -> None:
        rapport = Rapport(kind=RapportKind.DISCUSSION, content="Hello?", actor=None)
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            rapport.clean()
        assert "actor" in exc_info.value.message_dict

    @pytest.mark.django_db
    def test_discussion_with_actor_valid(self) -> None:
        character = CharacterFactory()
        rapport = Rapport(kind=RapportKind.DISCUSSION, content="Hello!", actor=character)
        # Must not raise
        rapport.clean()

    @pytest.mark.django_db
    def test_non_discussion_with_actor_raises(self) -> None:
        from django.core.exceptions import ValidationError

        character = CharacterFactory()
        rapport = Rapport(kind=RapportKind.DESCRIPTION, content="A scene.", actor=character)
        with pytest.raises(ValidationError) as exc_info:
            rapport.clean()
        assert "actor" in exc_info.value.message_dict

    def test_non_discussion_without_actor_valid(self) -> None:
        rapport = Rapport(kind=RapportKind.ACTION, content="She runs.", actor=None)
        # Must not raise
        rapport.clean()


@pytest.mark.django_db
class TestRapportOrdering:
    """DB tests for Rapport ordering."""

    def test_ordering_by_created_at(self) -> None:
        user = UserFactory()
        game = GameFactory(owner=user)
        report = ReportFactory(game=game, author=user)

        r1 = Rapport.objects.create(report=report, kind=RapportKind.DESCRIPTION, content="First")
        r2 = Rapport.objects.create(report=report, kind=RapportKind.ACTION, content="Second")
        r3 = Rapport.objects.create(report=report, kind=RapportKind.NARRATION, content="Third")

        qs = list(Rapport.objects.filter(report=report))
        assert qs[0].pk == r1.pk
        assert qs[1].pk == r2.pk
        assert qs[2].pk == r3.pk
