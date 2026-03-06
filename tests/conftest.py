"""
Pytest configuration and fixtures for Suddenly tests.
"""

import pytest

from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


@pytest.fixture(autouse=True)
def _celery_eager(settings):
    """Force Celery to execute tasks synchronously during tests."""
    from suddenly.celery import app as celery_app

    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture
def user(db):
    """Create a test user."""
    return UserFactory(
        username="testuser",
        email="test@example.com",
        display_name="Test User",
    )


@pytest.fixture
def other_user(db):
    """Create another test user."""
    return UserFactory(
        username="otheruser",
        email="other@example.com",
        display_name="Other User",
    )


@pytest.fixture
def game(db, user):
    """Create a test game."""
    return GameFactory(
        title="Test Game",
        description="A test game",
        game_system="Test System",
        owner=user,
        is_public=True,
    )


@pytest.fixture
def character(db, user, game):
    """Create a test NPC character."""
    return CharacterFactory(
        name="Test NPC",
        description="A test NPC",
        status="npc",
        creator=user,
        origin_game=game,
    )


@pytest.fixture
def pc_character(db, user, game):
    """Create a test PC character."""
    return CharacterFactory(
        name="Test PC",
        description="A test PC",
        status="pc",
        owner=user,
        creator=user,
        origin_game=game,
    )


@pytest.fixture
def report(db, user, game):
    """Create a test report."""
    return ReportFactory(
        title="Test Report",
        content="This is a test report content.",
        game=game,
        author=user,
        status="draft",
    )


@pytest.fixture
def api_client():
    """Create a DRF API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def client():
    """Create a Django test client."""
    from django.test import Client
    return Client()


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client
