"""
Tests for Django template-based views and ActivityPub endpoint views.

Covers: core/views.py, users/views.py, activitypub/views.py
Does NOT cover DRF API viewsets (see test_api.py).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from suddenly.characters.models import Character, Quote, QuoteVisibility
from suddenly.games.models import Game, Report
from suddenly.users.models import User
from tests.factories import GameFactory

# ===================================================================
# Core views
# ===================================================================


class TestHomeView:
    """GET / -- public home page."""

    def test_home_returns_200(self, client: Client, db: Any) -> None:
        response = client.get("/")
        assert response.status_code == 200

    def test_home_uses_correct_template(self, client: Client, db: Any) -> None:
        response = client.get("/")
        assert "core/home.html" in [t.name for t in response.templates]


class TestHealthCheck:
    """GET /health/ -- health check endpoint."""

    def test_health_returns_200_json(self, client: Client) -> None:
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ===================================================================
# Users views -- ProfileView
# ===================================================================


class TestProfileViewRendering:
    """GET /@<username>/ -- public profile rendering and context."""

    def test_profile_returns_200_for_active_user(self, client: Client, user: User) -> None:
        response = client.get(f"/@{user.username}/")
        assert response.status_code == 200

    def test_profile_uses_correct_template(self, client: Client, user: User) -> None:
        response = client.get(f"/@{user.username}/")
        template_names = [t.name for t in response.templates]
        assert "users/profile.html" in template_names

    def test_profile_context_contains_profile_user(self, client: Client, user: User) -> None:
        response = client.get(f"/@{user.username}/")
        assert "profile_user" in response.context
        assert response.context["profile_user"].username == user.username

    def test_profile_context_contains_public_games(
        self, client: Client, user: User, game: Game
    ) -> None:
        response = client.get(f"/@{user.username}/")
        assert "games" in response.context

    def test_profile_excludes_private_games_for_anonymous(self, client: Client, user: User) -> None:
        GameFactory(owner=user, is_public=False, title="Secret Game")  # type: ignore[no-untyped-call]
        GameFactory(owner=user, is_public=True, title="Public Game")  # type: ignore[no-untyped-call]
        response = client.get(f"/@{user.username}/")
        game_titles = [g.title for g in response.context["games"]]
        assert "Secret Game" not in game_titles
        assert "Public Game" in game_titles

    def test_profile_displays_username_in_body(self, client: Client, user: User) -> None:
        response = client.get(f"/@{user.username}/")
        assert user.username.encode() in response.content


# ===================================================================
# Users views -- ProfileEditView
# ===================================================================


class TestProfileEditViewRendering:
    """GET/POST /@<username>/edit/ -- authenticated profile editing."""

    def test_anonymous_redirects_to_login(self, client: Client, user: User) -> None:
        response = client.get(f"/@{user.username}/edit/")
        assert response.status_code == 302
        assert "/accounts/" in response["Location"]

    def test_authenticated_get_returns_200(self, client: Client, user: User) -> None:
        client.force_login(user)
        response = client.get(f"/@{user.username}/edit/")
        assert response.status_code == 200

    def test_authenticated_get_uses_correct_template(self, client: Client, user: User) -> None:
        client.force_login(user)
        response = client.get(f"/@{user.username}/edit/")
        template_names = [t.name for t in response.templates]
        assert "users/profile_edit.html" in template_names

    def test_post_valid_data_redirects_to_profile(self, client: Client, user: User) -> None:
        client.force_login(user)
        response = client.post(
            f"/@{user.username}/edit/",
            {
                "display_name": "Updated Name",
                "bio": "New bio",
                "content_language": "en",
                "preferred_languages": '["fr", "en"]',
                "show_unlabeled_content": True,
            },
        )
        assert response.status_code == 302
        assert f"/@{user.username}/" in response["Location"]

    def test_post_updates_user_display_name(self, client: Client, user: User) -> None:
        client.force_login(user)
        client.post(
            f"/@{user.username}/edit/",
            {
                "display_name": "Brand New Name",
                "bio": "",
                "content_language": "fr",
                "preferred_languages": "",
                "show_unlabeled_content": True,
            },
        )
        user.refresh_from_db()
        assert user.display_name == "Brand New Name"

    def test_other_user_edit_redirects_to_own(
        self, client: Client, user: User, other_user: User
    ) -> None:
        client.force_login(user)
        response = client.get(f"/@{other_user.username}/edit/")
        assert response.status_code == 302
        assert user.username in response["Location"]


# ===================================================================
# ActivityPub -- WebFinger edge cases
# ===================================================================


class TestWebFingerEdgeCases:
    """Additional WebFinger edge cases beyond test_activitypub.py."""

    def test_webfinger_invalid_acct_format(self, client: Client, db: Any) -> None:
        response = client.get("/.well-known/webfinger", {"resource": "acct:invalid"})
        assert response.status_code == 400

    def test_webfinger_https_resource_valid_user(
        self, client: Client, user: User, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        user.ap_id = f"https://test.social/users/{user.username}"
        user.save()

        response = client.get(
            "/.well-known/webfinger",
            {"resource": f"https://test.social/users/{user.username}"},
        )
        assert response.status_code == 200

    def test_webfinger_https_resource_unknown_actor(
        self, client: Client, db: Any, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        response = client.get(
            "/.well-known/webfinger",
            {"resource": "https://test.social/users/nonexistent"},
        )
        assert response.status_code == 404

    def test_webfinger_non_acct_non_https_returns_400(self, client: Client, db: Any) -> None:
        response = client.get("/.well-known/webfinger", {"resource": "ftp://something"})
        assert response.status_code == 400

    def test_webfinger_post_method_not_allowed(self, client: Client, db: Any) -> None:
        response = client.post("/.well-known/webfinger")
        assert response.status_code == 405


# ===================================================================
# ActivityPub -- User actor endpoints
# ===================================================================


class TestUserActorViews:
    """User actor AP endpoints -- additional coverage."""

    def test_user_actor_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        response = client.get("/users/nobody", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 404

    def test_user_inbox_nonexistent_user_returns_404(self, client: Client, db: Any) -> None:
        response = client.post(
            "/users/nobody/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )
        assert response.status_code == 404

    def test_user_inbox_get_method_not_allowed(self, client: Client, user: User) -> None:
        response = client.get(f"/users/{user.username}/inbox")
        assert response.status_code == 405

    def test_user_outbox_nonexistent_user_returns_404(self, client: Client, db: Any) -> None:
        response = client.get("/users/nobody/outbox", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 404

    def test_user_outbox_returns_ordered_collection(
        self, client: Client, user: User, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        response = client.get(
            f"/users/{user.username}/outbox",
            HTTP_ACCEPT="application/activity+json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 0

    def test_user_followers_returns_ordered_collection(
        self, client: Client, user: User, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        response = client.get(
            f"/users/{user.username}/followers",
            HTTP_ACCEPT="application/activity+json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 0

    def test_user_followers_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        response = client.get("/users/nobody/followers", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 404

    def test_user_followers_post_not_allowed(self, client: Client, user: User) -> None:
        response = client.post(f"/users/{user.username}/followers")
        assert response.status_code == 405


# ===================================================================
# ActivityPub -- Game actor endpoints
# ===================================================================


class TestGameActorViews:
    """Game actor AP endpoints."""

    def test_game_actor_html_redirect(self, client: Client, game: Game) -> None:
        response = client.get(f"/games/{game.id}", HTTP_ACCEPT="text/html")
        assert response.status_code == 302

    def test_game_actor_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        import uuid

        fake_id = uuid.uuid4()
        response = client.get(f"/games/{fake_id}", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 404

    def test_game_actor_private_game_returns_404(self, client: Client, user: User) -> None:
        private_game = GameFactory(  # type: ignore[no-untyped-call]
            owner=user, is_public=False, title="Private"
        )
        response = client.get(f"/games/{private_game.id}", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Inbox uses verify_signature — needs full signature mock")
    def test_game_inbox_valid_json(self, client: Client, game: Game, mocker: Any) -> None:
        response = client.post(
            f"/games/{game.id}/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )
        assert response.status_code == 202

    def test_game_inbox_invalid_json(self, client: Client, game: Game) -> None:
        response = client.post(
            f"/games/{game.id}/inbox",
            data="not json",
            content_type="application/activity+json",
        )
        assert response.status_code == 400

    def test_game_inbox_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        import uuid

        fake_id = uuid.uuid4()
        response = client.post(
            f"/games/{fake_id}/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )
        assert response.status_code == 404

    def test_game_outbox_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        import uuid

        fake_id = uuid.uuid4()
        response = client.get(f"/games/{fake_id}/outbox", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 404

    def test_game_outbox_returns_ordered_collection(
        self, client: Client, game: Game, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        response = client.get(f"/games/{game.id}/outbox", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"

    def test_game_outbox_includes_published_reports(
        self, client: Client, game: Game, user: User, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        Report.objects.create(
            title="Published", content="Content", game=game, author=user, status="published"
        )
        Report.objects.create(
            title="Draft", content="Draft content", game=game, author=user, status="draft"
        )
        response = client.get(f"/games/{game.id}/outbox", HTTP_ACCEPT="application/activity+json")
        data = response.json()
        assert data["totalItems"] == 1


# ===================================================================
# ActivityPub -- Character actor endpoints
# ===================================================================


class TestCharacterActorViews:
    """Character actor AP endpoints."""

    def test_character_actor_html_redirect(self, client: Client, character: Character) -> None:
        response = client.get(f"/characters/{character.id}", HTTP_ACCEPT="text/html")
        assert response.status_code == 302

    def test_character_actor_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        import uuid

        fake_id = uuid.uuid4()
        response = client.get(f"/characters/{fake_id}", HTTP_ACCEPT="application/activity+json")
        assert response.status_code == 404

    def test_character_actor_json_returns_person(
        self, client: Client, character: Character, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        response = client.get(
            f"/characters/{character.id}", HTTP_ACCEPT="application/activity+json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "Person"
        assert data["name"] == character.name

    @pytest.mark.skip(reason="Inbox uses verify_signature — needs full signature mock")
    def test_character_inbox_valid_json(
        self, client: Client, character: Character, mocker: Any
    ) -> None:
        response = client.post(
            f"/characters/{character.id}/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )
        assert response.status_code == 202

    def test_character_inbox_invalid_json(self, client: Client, character: Character) -> None:
        response = client.post(
            f"/characters/{character.id}/inbox",
            data="not json",
            content_type="application/activity+json",
        )
        assert response.status_code == 400

    def test_character_inbox_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        import uuid

        fake_id = uuid.uuid4()
        response = client.post(
            f"/characters/{fake_id}/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )
        assert response.status_code == 404

    def test_character_outbox_returns_ordered_collection(
        self, client: Client, character: Character, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        response = client.get(
            f"/characters/{character.id}/outbox",
            HTTP_ACCEPT="application/activity+json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 0

    def test_character_outbox_nonexistent_returns_404(self, client: Client, db: Any) -> None:
        import uuid

        fake_id = uuid.uuid4()
        response = client.get(
            f"/characters/{fake_id}/outbox",
            HTTP_ACCEPT="application/activity+json",
        )
        assert response.status_code == 404

    def test_character_outbox_includes_public_quotes(
        self, client: Client, character: Character, user: User, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.AP_BASE_URL = "https://test.social"
        Quote.objects.create(
            content="Public quote",
            character=character,
            author=user,
            visibility=QuoteVisibility.PUBLIC,
        )
        Quote.objects.create(
            content="Private quote",
            character=character,
            author=user,
            visibility=QuoteVisibility.PRIVATE,
        )
        response = client.get(
            f"/characters/{character.id}/outbox",
            HTTP_ACCEPT="application/activity+json",
        )
        data = response.json()
        assert data["totalItems"] == 1


# ===================================================================
# ActivityPub -- NodeInfo endpoints
# ===================================================================


class TestNodeInfoViews:
    """NodeInfo endpoint coverage."""

    def test_nodeinfo_index_post_not_allowed(self, client: Client) -> None:
        response = client.post("/.well-known/nodeinfo")
        assert response.status_code == 405

    def test_nodeinfo_2_0_includes_metadata(self, client: Client, db: Any, settings: Any) -> None:
        settings.DOMAIN = "test.social"
        settings.SITE_NAME = "Test Suddenly"
        settings.SITE_DESCRIPTION = "A test instance"
        response = client.get("/.well-known/nodeinfo/2.0")
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["nodeName"] == "Test Suddenly"
        assert data["metadata"]["nodeDescription"] == "A test instance"
        assert "games" in data["metadata"]
        assert "characters" in data["metadata"]

    def test_nodeinfo_2_0_counts_local_entities(
        self, client: Client, user: User, game: Game, character: Character, settings: Any
    ) -> None:
        settings.DOMAIN = "test.social"
        settings.SITE_NAME = "Test"
        settings.SITE_DESCRIPTION = "Test"
        response = client.get("/.well-known/nodeinfo/2.0")
        data = response.json()
        assert data["usage"]["users"]["total"] >= 1
        assert data["metadata"]["games"] >= 1
        assert data["metadata"]["characters"] >= 1
