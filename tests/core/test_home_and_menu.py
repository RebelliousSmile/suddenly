"""
Tests for the home/feed toggle, vitrine stats, and account-menu wiring.

Covers Front #1 (`/` renders the feed when authenticated), Front #2 (instance
stats on the anonymous vitrine), and Front #5 (account-menu links wired +
badge counts injected).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import (
    Character,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
)
from suddenly.core.models import Notification, NotificationType
from suddenly.games.models import Game
from suddenly.users.models import User


@pytest.fixture(autouse=True)
def _isolated_env(settings: Any) -> Any:
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    # The dev config uses a manifest static storage; there is no built manifest
    # in the test env, so fall back to the plain backend for template rendering.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    cache.clear()
    yield
    cache.clear()


class TestHomeToggle:
    def test_anonymous_home_renders_vitrine_with_stats(
        self, db: Any, client: Client, user: User, game: Game
    ) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.content.decode()
        # Vitrine markers: the hero gradient section + the instance stats band.
        assert "from-surface to-background" in body  # hero, vitrine-only
        assert "grid-stats" in body

    def test_authenticated_home_renders_feed(self, db: Any, client: Client, user: User) -> None:
        client.force_login(user)
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.content.decode()
        # Authenticated `/` serves the feed, not the vitrine hero.
        assert "from-surface to-background" not in body
        # The feed tab bar links to the three feed scopes.
        assert reverse("feed:home") in body
        assert reverse("feed:instance") in body
        assert reverse("feed:fediverse") in body


class TestAccountMenu:
    def test_menu_links_are_wired(self, db: Any, client: Client, user: User) -> None:
        client.force_login(user)
        body = client.get("/").content.decode()
        # The previously-dead account entries now resolve to real routes.
        assert reverse("characters:gm_dashboard") in body
        assert reverse("characters:link_requests") in body
        assert reverse("feed:notifications") in body

    def test_badge_counts_injected(
        self, db: Any, client: Client, user: User, other_user: User, character: Character
    ) -> None:
        # A pending link request targeting one of the user's characters...
        LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,  # created by `user`
            message="adopt",
            status=LinkRequestStatus.PENDING,
        )
        # ...and an unread notification for the user.
        Notification.objects.create(
            recipient=user,
            type=NotificationType.MENTION,
            message="hey",
            is_read=False,
        )

        client.force_login(user)

        # The context processor exposes both counts (rendered as badges).
        from suddenly.core.context_processors import account_badges

        class _Req:
            pass

        req = _Req()
        req.user = user  # type: ignore[attr-defined]
        ctx = account_badges(req)
        assert ctx["pending_requests_count"] == 1
        # The pending LinkRequest also auto-creates a notification (signal), so
        # the unread count reflects every unread notification for the user.
        expected_unread = Notification.objects.filter(recipient=user, is_read=False).count()
        assert expected_unread >= 1
        assert ctx["unread_notifications_count"] == expected_unread

    def test_badges_empty_for_anonymous(self, db: Any) -> None:
        from suddenly.core.context_processors import account_badges

        class _Anon:
            is_authenticated = False

        class _Req:
            user = _Anon()

        assert account_badges(_Req()) == {}
