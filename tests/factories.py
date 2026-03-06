# mypy: disable-error-code="no-untyped-call,type-arg,attr-defined"
"""
Factory Boy factories for Suddenly test suite.

factory_boy is an untyped library — mypy strict errors are suppressed
for this module only.
"""

from __future__ import annotations

import factory
from django.contrib.auth import get_user_model

from suddenly.characters.models import Character
from suddenly.games.models import Game, Report

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for User model."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    display_name = factory.LazyAttribute(lambda obj: f"User {obj.username}")


class GameFactory(factory.django.DjangoModelFactory):
    """Factory for Game model."""

    class Meta:
        model = Game

    title = factory.Sequence(lambda n: f"Game {n}")
    description = "A test game"
    game_system = "Test System"
    owner = factory.SubFactory(UserFactory)
    is_public = True


class CharacterFactory(factory.django.DjangoModelFactory):
    """Factory for Character model."""

    class Meta:
        model = Character

    name = factory.Sequence(lambda n: f"Character {n}")
    description = "A test character"
    status = "npc"
    creator = factory.SubFactory(UserFactory)
    origin_game = factory.SubFactory(GameFactory)


class ReportFactory(factory.django.DjangoModelFactory):
    """Factory for Report model."""

    class Meta:
        model = Report

    title = factory.Sequence(lambda n: f"Report {n}")
    content = "This is a test report content."
    author = factory.SubFactory(UserFactory)
    game = factory.SubFactory(GameFactory)
    status = "draft"
