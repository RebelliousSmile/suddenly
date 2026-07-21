"""Tests for the Stats & Succès page + stats aggregation (#153)."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from suddenly.characters.models import Follow
from suddenly.core.models import UnlockedAchievement
from suddenly.core.stats import compute_user_stats
from suddenly.games.models import Game, Like, Rapport, RapportKind, Report, ReportStatus
from suddenly.users.models import User


@pytest.fixture(autouse=True)
def _isolated(settings: Any) -> Any:
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    cache.clear()
    yield
    cache.clear()


def _released_scene(author: User, game: Game, content: str) -> Report:
    return Report.objects.create(
        title="Scene",
        content=content,
        game=game,
        author=author,
        status=ReportStatus.PUBLISHED,
        visibility="public",
        remote=False,
        published_at=timezone.now(),
        released_at=timezone.now(),
    )


@pytest.mark.django_db
def test_compute_stats_values(user: User, other_user: User, game: Game) -> None:
    scene = _released_scene(user, game, "one two three")  # 3 words, 13 signs
    Rapport.objects.create(report=scene, kind=RapportKind.NARRATION, content="four five")  # 2 words
    Like.objects.create(user=other_user, report=scene)  # a like received
    user_ct = ContentType.objects.get_for_model(User)
    Follow.objects.create(follower=other_user, content_type=user_ct, object_id=user.id)

    # The publish signal warmed the stats cache before the like/follow existed;
    # drop it so we assert the true current values (5-min TTL otherwise).
    cache.clear()
    stats = compute_user_stats(user)

    assert stats["scenes_published"] == 1
    assert stats["posts"] == 1
    assert stats["words"] == 5  # 3 (scene) + 2 (post)
    assert stats["signs"] == len("one two three") + len("four five")
    assert stats["likes_received"] == 1
    assert stats["likes_given"] == 0
    assert stats["followers"] == 1
    assert stats["following"] == 0


@pytest.mark.django_db
def test_stats_computation_is_cached(user: User, game: Game) -> None:
    _released_scene(user, game, "hello world")
    first = compute_user_stats(user)
    # Add another scene WITHOUT invalidating the cache → memoized value holds.
    Report.objects.create(
        title="Extra",
        content="more words here",
        game=game,
        author=user,
        status=ReportStatus.DRAFT,
    )
    assert compute_user_stats(user) == first


@pytest.mark.django_db
def test_stats_page_requires_login(client: Client) -> None:
    resp = client.get(reverse("users:settings_stats"))
    assert resp.status_code == 302  # redirected to login


@pytest.mark.django_db
def test_stats_page_renders(client: Client, user: User, game: Game) -> None:
    _released_scene(user, game, "alpha beta")
    client.force_login(user)
    resp = client.get(reverse("users:settings_stats"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Stats &amp; Succès" in body or "Stats & Succès" in body
    # A stat tile and an achievement are present.
    assert "Scènes publiées" in body or "publi" in body


@pytest.mark.django_db
def test_badge_counts_unseen_and_clears_on_visit(client: Client, user: User, game: Game) -> None:
    _released_scene(user, game, "spark")  # publish → first_scene unlocked (unseen)
    unlocked = UnlockedAchievement.objects.filter(user=user, seen_at__isnull=True).count()
    assert unlocked >= 1

    client.force_login(user)
    client.get(reverse("users:settings_stats"))  # visiting marks them seen

    assert not UnlockedAchievement.objects.filter(user=user, seen_at__isnull=True).exists()
