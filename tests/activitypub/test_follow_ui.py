"""
Follow UI coverage — local/remote toggle, followers/following lists, remote
profile enrichment (epic C, #133, Phase 5).

Complements `test_follow_federation.py` (inbox/outbox activity lifecycle) with
the user-facing surfaces: HTMX follow buttons on User/Character/Game (local
and remote Suddenly), paginated followers/following lists, and remote-profile
enrichment (criterion 3 — Suddenly vs Mastodon, never a 500 on a bad fetch).

`TestRemoteFollowToggle` in `tests/test_federation_e2e.py` already covers
`remote_follow_toggle` thoroughly for User targets — this file focuses its
remote-follow coverage on Character/Game targets (DEC-C4 polymorphic
classification), which have zero coverage elsewhere.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from suddenly.activitypub.models import FederatedServer
from suddenly.characters.models import Character, Follow
from suddenly.games.models import Game
from suddenly.users.models import User
from tests.factories import CharacterFactory, GameFactory, UserFactory

pytestmark = pytest.mark.django_db


# ─── Local follow_toggle (characters:follow_toggle) ──────────────────────


class TestLocalFollowToggle:
    """`characters.follow_views.follow_toggle` — polymorphic local toggle."""

    def test_get_not_allowed(self) -> None:
        user = UserFactory()
        client = Client()
        client.force_login(user)

        response = client.get(reverse("characters:follow_toggle"))

        assert response.status_code == 405

    def test_missing_params_bad_request(self) -> None:
        user = UserFactory()
        client = Client()
        client.force_login(user)

        response = client.post(reverse("characters:follow_toggle"), {})

        assert response.status_code == 400

    def test_invalid_target_type_bad_request(self) -> None:
        user = UserFactory()
        client = Client()
        client.force_login(user)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "spaceship", "target_id": str(user.pk)},
        )

        assert response.status_code == 400

    def test_anonymous_redirected_to_login(self) -> None:
        target = UserFactory()
        client = Client()

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "user", "target_id": str(target.pk)},
        )

        assert response.status_code == 302
        assert "login" in response.url

    def test_follow_user_creates_follow_record(self) -> None:
        follower = UserFactory()
        target = UserFactory()
        client = Client()
        client.force_login(follower)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "user", "target_id": str(target.pk)},
        )

        assert response.status_code == 200
        assert response.context["is_following"] is True
        ct = ContentType.objects.get_for_model(User)
        assert Follow.objects.filter(
            follower=follower, content_type=ct, object_id=target.pk
        ).exists()

    def test_follow_character_creates_follow_record(self) -> None:
        follower = UserFactory()
        target = CharacterFactory()
        client = Client()
        client.force_login(follower)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "character", "target_id": str(target.pk)},
        )

        assert response.status_code == 200
        assert response.context["is_following"] is True
        ct = ContentType.objects.get_for_model(Character)
        assert Follow.objects.filter(
            follower=follower, content_type=ct, object_id=target.pk
        ).exists()

    def test_follow_game_creates_follow_record(self) -> None:
        follower = UserFactory()
        target = GameFactory()
        client = Client()
        client.force_login(follower)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "game", "target_id": str(target.pk)},
        )

        assert response.status_code == 200
        assert response.context["is_following"] is True
        ct = ContentType.objects.get_for_model(Game)
        assert Follow.objects.filter(
            follower=follower, content_type=ct, object_id=target.pk
        ).exists()

    def test_second_post_unfollows(self) -> None:
        follower = UserFactory()
        target = CharacterFactory()
        client = Client()
        client.force_login(follower)
        payload = {"target_type": "character", "target_id": str(target.pk)}

        client.post(reverse("characters:follow_toggle"), payload)
        response = client.post(reverse("characters:follow_toggle"), payload)

        assert response.status_code == 200
        assert response.context["is_following"] is False
        ct = ContentType.objects.get_for_model(Character)
        assert not Follow.objects.filter(
            follower=follower, content_type=ct, object_id=target.pk
        ).exists()

    def test_self_follow_rejected(self) -> None:
        user = UserFactory()
        client = Client()
        client.force_login(user)

        response = client.post(
            reverse("characters:follow_toggle"),
            {"target_type": "user", "target_id": str(user.pk)},
        )

        assert response.status_code == 400


# ─── Remote follow toggle — Character/Game (DEC-C4) ───────────────────────


class TestRemoteFollowTogglePolymorphic:
    """`federation.remote_follow_toggle` for Character/Game targets.

    User-target coverage already lives in
    `tests/test_federation_e2e.py::TestRemoteFollowToggle` — not duplicated
    here. Every remote fetch is mocked at the network boundary
    (`suddenly.activitypub._http.fetch_ap_actor`), the resolution helpers
    (`get_or_create_remote_character`/`get_or_create_remote_game`) run for
    real against that mocked data (DEC-C4 polymorphic classification).
    """

    def test_follow_remote_character_creates_polymorphic_follow(self) -> None:
        FederatedServer.objects.create(
            server_name="peer.suddenly.test", application_type="suddenly"
        )
        character_url = "https://peer.suddenly.test/users/remote_npc"
        creator_url = "https://peer.suddenly.test/users/remote_creator"

        actors: dict[str, dict[str, Any]] = {
            character_url: {
                "type": "Person",
                "id": character_url,
                "name": "Remote NPC",
                "summary": "A mysterious stranger.",
                "status": "npc",
                "creator": creator_url,
                "inbox": f"{character_url}/inbox",
                "outbox": f"{character_url}/outbox",
            },
            creator_url: {
                "type": "Person",
                "id": creator_url,
                "preferredUsername": "remote_creator",
                "name": "Remote Creator",
                "inbox": f"{creator_url}/inbox",
            },
        }

        local_user = UserFactory()
        client = Client()
        client.force_login(local_user)

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor", side_effect=lambda url: actors.get(url)
            ),
            patch("suddenly.activitypub.tasks.send_follow_activity") as mock_task,
            patch("suddenly.activitypub.signals._safe_delay"),
        ):
            mock_task.delay = lambda *a, **k: None
            response = client.post(
                reverse("federation:remote_follow_toggle"), {"ap_id": character_url}
            )

        assert response.status_code == 200
        assert b"target_type" in response.content
        character = Character.objects.filter(ap_id=character_url).first()
        assert character is not None, "Remote Character mirror must be created"
        assert character.remote is True

        ct = ContentType.objects.get_for_model(Character)
        assert Follow.objects.filter(
            follower=local_user, content_type=ct, object_id=character.pk
        ).exists()

    def test_follow_remote_game_creates_polymorphic_follow(self) -> None:
        FederatedServer.objects.create(
            server_name="peer.suddenly.test", application_type="suddenly"
        )
        game_url = "https://peer.suddenly.test/games/remote_campaign"
        owner_url = "https://peer.suddenly.test/users/remote_gm"

        actors: dict[str, dict[str, Any]] = {
            game_url: {
                "type": "Group",
                "id": game_url,
                "name": "The Remote Campaign",
                "summary": "A campaign hosted elsewhere.",
                "attributedTo": owner_url,
                "inbox": f"{game_url}/inbox",
                "outbox": f"{game_url}/outbox",
            },
            owner_url: {
                "type": "Person",
                "id": owner_url,
                "preferredUsername": "remote_gm",
                "name": "Remote GM",
                "inbox": f"{owner_url}/inbox",
            },
        }

        local_user = UserFactory()
        client = Client()
        client.force_login(local_user)

        with (
            patch(
                "suddenly.activitypub._http.fetch_ap_actor", side_effect=lambda url: actors.get(url)
            ),
            patch("suddenly.activitypub.tasks.send_follow_activity") as mock_task,
            patch("suddenly.activitypub.signals._safe_delay"),
        ):
            mock_task.delay = lambda *a, **k: None
            response = client.post(reverse("federation:remote_follow_toggle"), {"ap_id": game_url})

        assert response.status_code == 200
        game = Game.objects.filter(ap_id=game_url).first()
        assert game is not None, "Remote Game mirror must be created"
        assert game.remote is True

        ct = ContentType.objects.get_for_model(Game)
        assert Follow.objects.filter(
            follower=local_user, content_type=ct, object_id=game.pk
        ).exists()

    def test_unreachable_actor_never_500s(self) -> None:
        local_user = UserFactory()
        client = Client()
        client.force_login(local_user)

        with patch("suddenly.activitypub._http.fetch_ap_actor", return_value=None):
            response = client.post(
                reverse("federation:remote_follow_toggle"),
                {"ap_id": "https://unreachable.example/users/ghost"},
            )

        assert response.status_code == 400


# ─── Followers / following paginated lists ────────────────────────────────


class TestFollowersFollowingLists:
    """`users.views.followers_list`/`following_list` — pagination + N+1 bound."""

    def test_followers_list_renders_and_bounds_queries(
        self, django_assert_max_num_queries: Any
    ) -> None:
        profile_user = UserFactory()
        followers = [UserFactory() for _ in range(3)]
        ct = ContentType.objects.get_for_model(User)
        for follower in followers:
            Follow.objects.create(follower=follower, content_type=ct, object_id=profile_user.id)

        client = Client()
        url = reverse("users:followers", kwargs={"username": profile_user.username})

        # Warm-up: neutralize first-miss cache writes unrelated to N (instance
        # settings, sessions) so the bounded assertion reflects query shape.
        client.get(url)
        with django_assert_max_num_queries(10):
            response = client.get(url)

        assert response.status_code == 200
        for follower in followers:
            assert follower.username.encode() in response.content

    def test_followers_list_query_count_independent_of_follower_count(self) -> None:
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        small_profile = UserFactory()
        for _ in range(2):
            follower = UserFactory()
            Follow.objects.create(
                follower=follower,
                content_type=ContentType.objects.get_for_model(User),
                object_id=small_profile.id,
            )

        large_profile = UserFactory()
        for _ in range(8):
            follower = UserFactory()
            Follow.objects.create(
                follower=follower,
                content_type=ContentType.objects.get_for_model(User),
                object_id=large_profile.id,
            )

        client = Client()
        small_url = reverse("users:followers", kwargs={"username": small_profile.username})
        large_url = reverse("users:followers", kwargs={"username": large_profile.username})

        # Warm-up both to prime any first-miss caches before measuring.
        client.get(small_url)
        client.get(large_url)

        with CaptureQueriesContext(connection) as small_ctx:
            client.get(small_url)
        with CaptureQueriesContext(connection) as large_ctx:
            client.get(large_url)

        assert len(small_ctx.captured_queries) == len(large_ctx.captured_queries), (
            "followers_list must not N+1 — query count must be independent of follower count"
        )

    def test_following_list_renders_polymorphic_targets(self) -> None:
        profile_user = UserFactory()
        followed_user = UserFactory()
        followed_character = CharacterFactory()
        followed_game = GameFactory()

        Follow.objects.create(
            follower=profile_user,
            content_type=ContentType.objects.get_for_model(User),
            object_id=followed_user.id,
        )
        Follow.objects.create(
            follower=profile_user,
            content_type=ContentType.objects.get_for_model(Character),
            object_id=followed_character.id,
        )
        Follow.objects.create(
            follower=profile_user,
            content_type=ContentType.objects.get_for_model(Game),
            object_id=followed_game.id,
        )

        client = Client()
        response = client.get(
            reverse("users:following", kwargs={"username": profile_user.username})
        )

        assert response.status_code == 200
        assert followed_user.username.encode() in response.content
        assert followed_character.name.encode() in response.content
        assert followed_game.title.encode() in response.content

    def test_following_list_query_count_independent_of_following_count(self) -> None:
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        small_profile = UserFactory()
        Follow.objects.create(
            follower=small_profile,
            content_type=ContentType.objects.get_for_model(User),
            object_id=UserFactory().id,
        )

        large_profile = UserFactory()
        for _ in range(6):
            Follow.objects.create(
                follower=large_profile,
                content_type=ContentType.objects.get_for_model(User),
                object_id=UserFactory().id,
            )
        for _ in range(4):
            Follow.objects.create(
                follower=large_profile,
                content_type=ContentType.objects.get_for_model(Character),
                object_id=CharacterFactory().id,
            )

        client = Client()
        small_url = reverse("users:following", kwargs={"username": small_profile.username})
        large_url = reverse("users:following", kwargs={"username": large_profile.username})

        client.get(small_url)
        client.get(large_url)

        with CaptureQueriesContext(connection) as small_ctx:
            client.get(small_url)
        with CaptureQueriesContext(connection) as large_ctx:
            client.get(large_url)

        # Bounded by distinct content types present (2 here), not by N of rows.
        assert len(large_ctx.captured_queries) <= len(small_ctx.captured_queries) + 3

    def test_followers_pagination_sentinel_present_when_has_next(self) -> None:
        profile_user = UserFactory()
        ct = ContentType.objects.get_for_model(User)
        for _ in range(25):
            Follow.objects.create(
                follower=UserFactory(), content_type=ct, object_id=profile_user.id
            )

        client = Client()
        url = reverse("users:followers", kwargs={"username": profile_user.username})

        page1 = client.get(url)
        assert page1.status_code == 200
        assert b'hx-trigger="revealed"' in page1.content

        page2 = client.get(url, {"page": 2})
        assert page2.status_code == 200
        assert b'hx-trigger="revealed"' not in page2.content

    def test_profile_counters_link_to_lists(self) -> None:
        profile_user = UserFactory()
        client = Client()

        response = client.get(reverse("users:profile", kwargs={"username": profile_user.username}))

        assert response.status_code == 200
        followers_url = reverse("users:followers", kwargs={"username": profile_user.username})
        following_url = reverse("users:following", kwargs={"username": profile_user.username})
        assert followers_url.encode() in response.content
        assert following_url.encode() in response.content


# ─── Remote profile enrichment (criterion 3) ──────────────────────────────


class TestRemoteProfileEnrichment:
    """`federation.remote_profile` + `follow_federation.fetch_remote_actor_collections`."""

    def test_suddenly_actor_shows_games_characters_activity(self) -> None:
        FederatedServer.objects.create(
            server_name="peer.suddenly.test", application_type="suddenly"
        )
        ap_id = "https://peer.suddenly.test/users/alice"
        outbox_url = f"{ap_id}/outbox"
        game_url = "https://peer.suddenly.test/games/ruins-campaign"
        character_url = "https://peer.suddenly.test/characters/zara"

        actor_data = {
            "type": "Person",
            "id": ap_id,
            "preferredUsername": "alice",
            "name": "Alice",
            "outbox": outbox_url,
        }
        outbox_data = {
            "orderedItems": [
                {
                    "type": "Article",
                    "id": "https://peer.suddenly.test/reports/1",
                    "name": "Session 1",
                    "content": "The party explored the ruins.",
                    "url": "https://peer.suddenly.test/reports/1",
                    "published": "2026-01-01T00:00:00Z",
                    "context": game_url,
                    "tag": [{"type": "Mention", "href": character_url, "name": "@Zara"}],
                }
            ]
        }
        game_actor_data = {"type": "Group", "id": game_url, "name": "The Ruins Campaign"}

        def fake_fetch_actor(url: str) -> dict[str, Any] | None:
            if url == ap_id:
                return actor_data
            if url == game_url:
                return game_actor_data
            return None

        client = Client()

        with (
            patch("suddenly.activitypub._http.fetch_ap_actor", side_effect=fake_fetch_actor),
            patch("suddenly.activitypub._http.fetch_ap_json", return_value=outbox_data),
        ):
            response = client.get(reverse("federation:remote_profile"), {"ap_id": ap_id})

        assert response.status_code == 200
        content = response.content
        assert b"Session 1" in content
        assert b"The Ruins Campaign" in content
        assert b"Zara" in content

    def test_mastodon_actor_shows_activity_only_no_suddenly_sections(self) -> None:
        # No FederatedServer row for this domain -> unknown -> not Suddenly.
        ap_id = "https://mastodon.example/users/bob"
        outbox_url = f"{ap_id}/outbox"

        actor_data = {
            "type": "Person",
            "id": ap_id,
            "preferredUsername": "bob",
            "name": "Bob",
            "outbox": outbox_url,
        }
        outbox_data = {
            "orderedItems": [
                {
                    "type": "Note",
                    "id": f"{ap_id}/statuses/1",
                    "content": "Hello fediverse from Mastodon",
                    "url": f"{ap_id}/statuses/1",
                    "published": "2026-01-01T00:00:00Z",
                }
            ]
        }

        def fake_fetch_actor(url: str) -> dict[str, Any] | None:
            return actor_data if url == ap_id else None

        client = Client()

        with (
            patch("suddenly.activitypub._http.fetch_ap_actor", side_effect=fake_fetch_actor),
            patch("suddenly.activitypub._http.fetch_ap_json", return_value=outbox_data),
        ):
            response = client.get(reverse("federation:remote_profile"), {"ap_id": ap_id})

        assert response.status_code == 200
        content = response.content
        assert b"Hello fediverse" in content
        assert b"No games to show" not in content
        assert b"No characters to show" not in content

    def test_javascript_scheme_url_stripped_reflected_xss(self) -> None:
        """Fix for review blocker: a hostile outbox must not smuggle a
        `javascript:` scheme into a rendered `<a href>` (reflected XSS).

        Django's autoescape neutralizes HTML metacharacters but not URL
        schemes — `_safe_url` in `follow_federation.py` is the server-side
        gate that must strip any non-http(s) scheme before it reaches the
        template context.
        """
        FederatedServer.objects.create(
            server_name="peer.suddenly.test", application_type="suddenly"
        )
        ap_id = "https://peer.suddenly.test/users/mallory"
        outbox_url = f"{ap_id}/outbox"
        game_url = "javascript:alert(1)"
        character_url = "javascript:alert(2)"

        actor_data = {
            "type": "Person",
            "id": ap_id,
            "preferredUsername": "mallory",
            "name": "Mallory",
            "outbox": outbox_url,
        }
        outbox_data = {
            "orderedItems": [
                {
                    "type": "Article",
                    # Both the `id` fallback and `url` are javascript: here —
                    # `_summarize_activity_item` falls back from `url` to
                    # `id` when `url` is unsafe, so exercising the attack
                    # with only `url` poisoned would let the (safe) `id`
                    # mask the assertion. Poisoning both proves the fallback
                    # itself is also gated by `_safe_url`.
                    "id": "javascript:alert(4)",
                    "name": "Malicious report",
                    "content": "Click me.",
                    "url": "javascript:alert(3)",
                    "published": "2026-01-01T00:00:00Z",
                    "context": game_url,
                    "tag": [{"type": "Mention", "href": character_url, "name": "@Evil"}],
                }
            ]
        }
        game_actor_data = {"type": "Group", "id": game_url, "name": "Evil Campaign"}

        def fake_fetch_actor(url: str) -> dict[str, Any] | None:
            if url == ap_id:
                return actor_data
            if url == game_url:
                return game_actor_data
            return None

        client = Client()

        with (
            patch("suddenly.activitypub._http.fetch_ap_actor", side_effect=fake_fetch_actor),
            patch("suddenly.activitypub._http.fetch_ap_json", return_value=outbox_data),
        ):
            response = client.get(reverse("federation:remote_profile"), {"ap_id": ap_id})

        assert response.status_code == 200
        assert b"javascript:" not in response.content

        assert response.context["activity"][0]["url"] == ""
        # The game context IRI itself is javascript: -> `_fetch_actor_summary`
        # rejects it before returning a summary, so it must be dropped
        # entirely from the games list.
        assert response.context["remote_games"] == []
        assert response.context["remote_characters"] == []

    def test_unreachable_outbox_degrades_to_empty_sections_never_500(self) -> None:
        FederatedServer.objects.create(
            server_name="peer.suddenly.test", application_type="suddenly"
        )
        ap_id = "https://peer.suddenly.test/users/carol"
        outbox_url = f"{ap_id}/outbox"

        actor_data = {
            "type": "Person",
            "id": ap_id,
            "preferredUsername": "carol",
            "name": "Carol",
            "outbox": outbox_url,
        }

        def fake_fetch_actor(url: str) -> dict[str, Any] | None:
            return actor_data if url == ap_id else None

        client = Client()

        with (
            patch("suddenly.activitypub._http.fetch_ap_actor", side_effect=fake_fetch_actor),
            patch(
                "suddenly.activitypub._http.fetch_ap_json", side_effect=Exception("network boom")
            ),
        ):
            response = client.get(reverse("federation:remote_profile"), {"ap_id": ap_id})

        assert response.status_code == 200
        assert b"No recent activity to show" in response.content
        assert b"No games to show" in response.content
        assert b"No characters to show" in response.content

    def test_actor_fetch_failure_never_500s(self) -> None:
        client = Client()

        with patch("suddenly.activitypub._http.fetch_ap_actor", return_value=None):
            response = client.get(
                reverse("federation:remote_profile"),
                {"ap_id": "https://unreachable.example/users/ghost"},
            )

        assert response.status_code == 200


# ─── AP-JSON collection endpoints (review finding #3 — no permanent test) ──


class TestActivityPubCollectionEndpoints:
    """`activitypub.views.user_following`/`game_followers`/`character_followers`.

    A temporary smoke test for these routes was removed without a permanent
    replacement (review finding, epic C #133) — this closes that gap.
    """

    def test_user_following_returns_ordered_collection(self, client: Client) -> None:
        follower = UserFactory()
        target = UserFactory()
        ct = ContentType.objects.get_for_model(User)
        Follow.objects.create(follower=follower, content_type=ct, object_id=target.pk)

        response = client.get(reverse("user-following", args=[follower.username]))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/activity+json"
        data = response.json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 1
        assert data["orderedItems"] == [target.actor_url]

    def test_user_following_empty_reports_zero_total(self, client: Client) -> None:
        follower = UserFactory()

        response = client.get(reverse("user-following", args=[follower.username]))

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 0
        assert data["orderedItems"] == []

    def test_game_followers_returns_ordered_collection(self, client: Client) -> None:
        game = GameFactory()
        follower1 = UserFactory()
        follower2 = UserFactory()
        ct = ContentType.objects.get_for_model(Game)
        Follow.objects.create(follower=follower1, content_type=ct, object_id=game.pk)
        Follow.objects.create(follower=follower2, content_type=ct, object_id=game.pk)

        response = client.get(reverse("game-followers", args=[game.pk]))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/activity+json"
        data = response.json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 2
        assert set(data["orderedItems"]) == {follower1.actor_url, follower2.actor_url}

    def test_character_followers_returns_ordered_collection(self, client: Client) -> None:
        character = CharacterFactory()
        follower = UserFactory()
        ct = ContentType.objects.get_for_model(Character)
        Follow.objects.create(follower=follower, content_type=ct, object_id=character.pk)

        response = client.get(reverse("character-followers", args=[character.pk]))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/activity+json"
        data = response.json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 1
        assert data["orderedItems"] == [follower.actor_url]
