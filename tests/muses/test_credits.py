"""Tests for Muses credit gating and atomic debiting."""

from __future__ import annotations

import pytest
from django.test import override_settings

from suddenly.muses.credits import can_use_muses, debit, has_credits
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

ENABLED = dict(
    SUDDENLY_MUSES_ENABLED=True,
    SUDDENLY_MUSES_URL="https://muse.example.test",
    SUDDENLY_MUSES_API_KEY="k",
)


def test_has_credits() -> None:
    assert has_credits(UserFactory(muses_credits=1)) is True
    assert has_credits(UserFactory(muses_credits=0)) is False
    assert has_credits(UserFactory(muses_credits=3), amount=3) is True
    assert has_credits(UserFactory(muses_credits=2), amount=3) is False


@override_settings(**ENABLED)
def test_can_use_requires_all_three() -> None:
    assert can_use_muses(UserFactory(muses_enabled=True, muses_credits=1)) is True
    assert can_use_muses(UserFactory(muses_enabled=False, muses_credits=1)) is False
    assert can_use_muses(UserFactory(muses_enabled=True, muses_credits=0)) is False


@override_settings(SUDDENLY_MUSES_ENABLED=False)
def test_can_use_false_when_hub_disabled() -> None:
    assert can_use_muses(UserFactory(muses_enabled=True, muses_credits=5)) is False


def test_debit_decrements_and_persists() -> None:
    user = UserFactory(muses_credits=2)
    assert debit(user) is True
    user.refresh_from_db()
    assert user.muses_credits == 1


def test_debit_floors_at_zero() -> None:
    user = UserFactory(muses_credits=0)
    assert debit(user) is False
    user.refresh_from_db()
    assert user.muses_credits == 0


def test_debit_amount() -> None:
    user = UserFactory(muses_credits=5)
    assert debit(user, amount=3) is True
    user.refresh_from_db()
    assert user.muses_credits == 2
    # Not enough for another 3.
    assert debit(user, amount=3) is False
    user.refresh_from_db()
    assert user.muses_credits == 2
