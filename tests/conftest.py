"""
Pytest configuration and fixtures for Suddenly tests.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from suddenly.characters.models import Character
from suddenly.games.models import Game, Report
from suddenly.users.models import User
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


@pytest.fixture(autouse=True)
def _celery_eager(settings: Any) -> None:
    """Force Celery to execute tasks synchronously during tests."""
    from suddenly.celery import app as celery_app

    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture
def user(db: Any) -> User:
    """Create a test user."""
    return UserFactory(  # type: ignore[return-value,no-untyped-call]
        username="testuser",
        email="test@example.com",
        display_name="Test User",
    )


@pytest.fixture
def other_user(db: Any) -> User:
    """Create another test user."""
    return UserFactory(  # type: ignore[return-value,no-untyped-call]
        username="otheruser",
        email="other@example.com",
        display_name="Other User",
    )


@pytest.fixture
def game(db: Any, user: User) -> Game:
    """Create a test game."""
    return GameFactory(  # type: ignore[return-value,no-untyped-call]
        title="Test Game",
        description="A test game",
        game_system="Test System",
        owner=user,
        is_public=True,
    )


@pytest.fixture
def character(db: Any, user: User, game: Game) -> Character:
    """Create a test NPC character."""
    return CharacterFactory(  # type: ignore[return-value,no-untyped-call]
        name="Test NPC",
        description="A test NPC",
        status="npc",
        creator=user,
        origin_game=game,
    )


@pytest.fixture
def pc_character(db: Any, user: User, game: Game) -> Character:
    """Create a test PC character."""
    return CharacterFactory(  # type: ignore[return-value,no-untyped-call]
        name="Test PC",
        description="A test PC",
        status="pc",
        owner=user,
        creator=user,
        origin_game=game,
    )


@pytest.fixture
def report(db: Any, user: User, game: Game) -> Report:
    """Create a test report."""
    return ReportFactory(  # type: ignore[return-value,no-untyped-call]
        title="Test Report",
        content="This is a test report content.",
        game=game,
        author=user,
        status="draft",
    )


@pytest.fixture
def api_client() -> Any:
    """Create a DRF API client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def client() -> Client:
    """Create a Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(api_client: Any, user: User) -> Any:
    """Create an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client
