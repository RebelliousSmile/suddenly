"""Tests for the feed promocard interleaving (SUD-P1)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from suddenly.characters.models import Follow
from suddenly.core.feed_views import interleave_promos
from suddenly.games.models import ReportStatus, ReportVisibility
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _types(items: list[dict[str, Any]]) -> list[str]:
    return [it["type"] for it in items]


# ---------------------------------------------------------------------------
# interleave_promos — unit
# ---------------------------------------------------------------------------


def test_interleave_inserts_every_n() -> None:
    reports = [f"r{i}" for i in range(6)]
    npcs = ["n0", "n1"]
    items = interleave_promos(reports, npcs, every=3)
    # r r r promo r r r promo
    assert _types(items) == [
        "report",
        "report",
        "report",
        "promo",
        "report",
        "report",
        "report",
        "promo",
    ]


def test_interleave_short_feed_guarantees_one_promo() -> None:
    reports = ["r0", "r1"]  # shorter than `every`
    npcs = ["n0"]
    items = interleave_promos(reports, npcs, every=6)
    assert _types(items) == ["report", "report", "promo"]


def test_interleave_empty_feed_has_no_promo() -> None:
    assert interleave_promos([], ["n0"], every=6) == []


def test_interleave_no_npcs_no_promo() -> None:
    reports = ["r0", "r1", "r2"]
    items = interleave_promos(reports, [], every=1)
    assert _types(items) == ["report", "report", "report"]


def test_interleave_stops_when_npcs_exhausted() -> None:
    reports = [f"r{i}" for i in range(9)]
    npcs = ["n0"]  # only one promo available
    items = interleave_promos(reports, npcs, every=3)
    assert _types(items).count("promo") == 1


def test_interleave_promo_carries_object() -> None:
    items = interleave_promos(["r0"], ["npc-obj"], every=6)
    promo = next(it for it in items if it["type"] == "promo")
    assert promo["obj"] == "npc-obj"


# ---------------------------------------------------------------------------
# feed_home integration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_feed_home_interleaves_promocards(client: Client, settings: Any) -> None:
    settings.FEED_PROMO_EVERY = 6
    from django.contrib.contenttypes.models import ContentType

    from suddenly.games.models import Game

    viewer = UserFactory()
    author = UserFactory()
    game = GameFactory(owner=author)

    # Follow the game so its reports and NPCs appear.
    Follow.objects.create(
        follower=viewer,
        content_type=ContentType.objects.get_for_model(Game),
        object_id=game.pk,
    )

    ReportFactory(
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
    )
    CharacterFactory(status="npc", origin_game=game, creator=author, remote=False)

    client.force_login(viewer)
    response = client.get(reverse("feed:home"))
    assert response.status_code == 200
    feed_items = response.context["feed_items"]
    assert "promo" in _types(feed_items)  # short feed → at least one promo


# ---------------------------------------------------------------------------
# Composer sidebar — feed_home / feed_instance / feed_fediverse
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_feed_home_sidebar_present(client: Client) -> None:
    user = UserFactory()
    client.force_login(user)
    response = client.get(reverse("feed:home"))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="composer"' in body


@pytest.mark.django_db
def test_feed_instance_anonymous_no_sidebar(client: Client) -> None:
    response = client.get(reverse("feed:instance"))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="composer"' not in body


@pytest.mark.django_db
def test_feed_instance_authenticated_has_sidebar(client: Client) -> None:
    user = UserFactory()
    client.force_login(user)
    response = client.get(reverse("feed:instance"))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="composer"' in body


@pytest.mark.django_db
def test_feed_htmx_swap_no_sidebar(client: Client) -> None:
    """A tab switch (HTMX) only swaps #feed-content — no composer context is built."""
    user = UserFactory()
    client.force_login(user)
    response = client.get(reverse("feed:fediverse"), HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="composer"' not in body
    assert "games" not in response.context


@pytest.mark.django_db
def test_feed_mobile_entry_point(client: Client) -> None:
    user = UserFactory()
    client.force_login(user)
    response = client.get(reverse("feed:home"))
    body = response.content.decode()
    assert reverse("games:composer") in body
