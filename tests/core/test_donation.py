"""
Tests for the donation-prompt system (US: donation nudges).

Covers audit gap #6 (session 2026-05-17): the usage-tracking + donation-prompt
logic in ``core.notification_signals._track_usage_and_prompt`` and the
``UserUsageStats.should_prompt`` rule had no behavioural tests.

Exercised behaviours:
- publishing a report increments ``UserUsageStats.total_posts``
- a ``DonationPrompt`` + notification are created every N posts
- no prompt when the user already donated this month
- nothing happens at all when donations are disabled instance-wide
- ``should_prompt(interval=...)`` boundary behaviour
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.cache import cache

from suddenly.core.models import (
    DonationPrompt,
    InstanceSettings,
    Notification,
    NotificationType,
    UserUsageStats,
)
from suddenly.games.models import Game, ReportStatus
from suddenly.users.models import User
from tests.factories import ReportFactory


@pytest.fixture(autouse=True)
def _isolated_cache(settings: Any) -> Any:
    """
    Use an in-memory cache and clear it around each test.

    ``InstanceSettings.get()`` memoises the singleton for 5 minutes; an isolated
    cache keeps the donation toggle deterministic and independent of the DB
    cache table.
    """
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    cache.clear()
    yield
    cache.clear()


def _enable_donations(interval: int = 10) -> InstanceSettings:
    settings_obj = InstanceSettings.get()
    settings_obj.donation_enabled = True
    settings_obj.donation_prompt_interval = interval
    settings_obj.save()  # save() busts the cache
    return settings_obj


def _publish_report(author: User, game: Game) -> None:
    """Publish one report authored by ``author`` (fires the usage signal once)."""
    ReportFactory(author=author, game=game, status=ReportStatus.PUBLISHED)


class TestUsageTracking:
    def test_publishing_increments_total_posts(self, db: Any, user: User, game: Game) -> None:
        _enable_donations(interval=100)  # high interval → no prompt yet

        _publish_report(user, game)

        stats = UserUsageStats.objects.get(user=user)
        assert stats.total_posts == 1
        assert stats.posts_since_last_prompt == 1

    def test_prompt_and_notification_created_every_n_posts(
        self, db: Any, user: User, game: Game
    ) -> None:
        _enable_donations(interval=3)

        for _ in range(3):
            _publish_report(user, game)

        prompt = DonationPrompt.objects.get(user=user)
        assert prompt.posts_at_prompt == 3

        # The counter is reset after prompting.
        stats = UserUsageStats.objects.get(user=user)
        assert stats.total_posts == 3
        assert stats.posts_since_last_prompt == 0

        # A donation invitation notification is sent to the author.
        note = Notification.objects.get(recipient=user, type=NotificationType.INVITATION)
        assert "3 comptes-rendus" in note.message

    def test_no_second_prompt_before_next_interval(self, db: Any, user: User, game: Game) -> None:
        _enable_donations(interval=3)

        for _ in range(4):  # one past the threshold
            _publish_report(user, game)

        # Still exactly one prompt: the 4th post has not reached the next window.
        assert DonationPrompt.objects.filter(user=user).count() == 1
        stats = UserUsageStats.objects.get(user=user)
        assert stats.posts_since_last_prompt == 1

    def test_no_prompt_if_donated_this_month(self, db: Any, user: User, game: Game) -> None:
        from django.utils import timezone

        _enable_donations(interval=1)
        UserUsageStats.objects.create(
            user=user,
            posts_since_last_prompt=5,
            last_donation_date=timezone.now().date(),
        )

        _publish_report(user, game)

        # The post is still counted...
        stats = UserUsageStats.objects.get(user=user)
        assert stats.total_posts == 1
        # ...but no prompt is generated because the user donated this month.
        assert not DonationPrompt.objects.filter(user=user).exists()

    def test_nothing_happens_when_donations_disabled(self, db: Any, user: User, game: Game) -> None:
        # Donations are disabled by default (InstanceSettings.donation_enabled=False).
        _publish_report(user, game)

        assert not UserUsageStats.objects.filter(user=user).exists()
        assert not DonationPrompt.objects.filter(user=user).exists()
        assert not Notification.objects.filter(
            recipient=user, type=NotificationType.INVITATION
        ).exists()


class TestShouldPrompt:
    def test_false_below_interval(self, db: Any, user: User) -> None:
        stats = UserUsageStats.objects.create(user=user, posts_since_last_prompt=9)
        assert stats.should_prompt(interval=10) is False

    def test_true_at_interval(self, db: Any, user: User) -> None:
        stats = UserUsageStats.objects.create(user=user, posts_since_last_prompt=10)
        assert stats.should_prompt(interval=10) is True

    def test_true_above_interval(self, db: Any, user: User) -> None:
        stats = UserUsageStats.objects.create(user=user, posts_since_last_prompt=11)
        assert stats.should_prompt(interval=10) is True

    def test_false_when_donated_this_month_even_above_interval(self, db: Any, user: User) -> None:
        from django.utils import timezone

        stats = UserUsageStats.objects.create(
            user=user,
            posts_since_last_prompt=50,
            last_donation_date=timezone.now().date(),
        )
        assert stats.should_prompt(interval=10) is False
