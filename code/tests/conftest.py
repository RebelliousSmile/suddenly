"""
Pytest configuration and fixtures for Suddenly tests.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        display_name="Test User"
    )


@pytest.fixture
def other_user(db):
    """Create another test user."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="testpass123",
        display_name="Other User"
    )


@pytest.fixture
def game(db, user):
    """Create a test game."""
    from suddenly.games.models import Game
    
    return Game.objects.create(
        title="Test Game",
        description="A test game",
        game_system="Test System",
        owner=user,
        is_public=True
    )


@pytest.fixture
def character(db, user, game):
    """Create a test NPC character."""
    from suddenly.characters.models import Character
    
    return Character.objects.create(
        name="Test NPC",
        description="A test NPC",
        status="npc",
        creator=user,
        origin_game=game
    )


@pytest.fixture
def pc_character(db, user, game):
    """Create a test PC character."""
    from suddenly.characters.models import Character
    
    return Character.objects.create(
        name="Test PC",
        description="A test PC",
        status="pc",
        owner=user,
        creator=user,
        origin_game=game
    )


@pytest.fixture
def report(db, user, game):
    """Create a test report."""
    from suddenly.games.models import Report
    
    return Report.objects.create(
        title="Test Report",
        content="This is a test report content.",
        game=game,
        author=user,
        status="draft"
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
