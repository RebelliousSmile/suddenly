"""Tests for the achievements (succès) catalogue + unlock service (#153)."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.utils import timezone

from suddenly.characters.models import Follow
from suddenly.core.achievements import evaluate_and_unlock
from suddenly.core.models import Notification, NotificationType, UnlockedAchievement
from suddenly.games.models import Game, Report, ReportStatus
from suddenly.users.models import User


@pytest.fixture(autouse=True)
def _cache(settings: Any) -> Any:
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    cache.clear()
    yield
    cache.clear()


def _released_scene(author: User, game: Game, content: str = "Body.") -> Report:
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
def test_evaluate_unlocks_and_notifies(user: User, other_user: User) -> None:
    # first_follower is NOT driven by the publish signal → tests the service in
    # isolation (a scene-based one would already be unlocked by the signal).
    user_ct = ContentType.objects.get_for_model(User)
    Follow.objects.create(follower=other_user, content_type=user_ct, object_id=user.id)

    new = evaluate_and_unlock(user)

    assert "first_follower" in new
    assert UnlockedAchievement.objects.filter(user=user, key="first_follower").exists()
    assert (
        Notification.objects.filter(recipient=user, type=NotificationType.ACHIEVEMENT).count() == 1
    )


@pytest.mark.django_db
def test_locked_until_threshold(user: User) -> None:
    # No scene → first_scene stays locked, no notification.
    assert evaluate_and_unlock(user) == []
    assert not UnlockedAchievement.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_unlock_is_idempotent(user: User, game: Game) -> None:
    _released_scene(user, game)
    evaluate_and_unlock(user)
    cache.clear()  # force a fresh stats recompute on the second pass

    second = evaluate_and_unlock(user)

    assert second == []  # nothing new
    assert UnlockedAchievement.objects.filter(user=user, key="first_scene").count() == 1
    assert (
        Notification.objects.filter(recipient=user, type=NotificationType.ACHIEVEMENT).count() == 1
    )


@pytest.mark.django_db
def test_publishing_a_scene_triggers_unlock_via_signal(user: User, game: Game) -> None:
    # No explicit evaluate_and_unlock call — the publish signal must do it inline.
    _released_scene(user, game)

    assert UnlockedAchievement.objects.filter(user=user, key="first_scene").exists()
