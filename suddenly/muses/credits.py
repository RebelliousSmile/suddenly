"""Credit gating and debiting for Muses features.

A user may use a Muses feature only when all three hold:

1. the instance is connected to the hub (:meth:`MusesClient.is_enabled`),
2. the user has activated Muses for their account (``muses_enabled``), and
3. the user has at least one credit left (``muses_credits``).

Debiting is atomic (an ``F`` update guarded by ``muses_credits__gte``), so two
concurrent uses can never drive the balance negative. Kept model-agnostic —
these helpers operate on any user instance carrying the two fields.
"""

from __future__ import annotations

from typing import Any

from django.db.models import F

from .client import MusesClient


def has_credits(user: Any, amount: int = 1) -> bool:
    """True if the account holds at least ``amount`` credits."""
    return int(getattr(user, "muses_credits", 0)) >= amount


def can_use_muses(user: Any) -> bool:
    """True if the user may spend a credit on a Muses feature right now."""
    return (
        bool(getattr(user, "muses_enabled", False))
        and MusesClient.is_enabled()
        and has_credits(user)
    )


def debit(user: Any, amount: int = 1) -> bool:
    """Atomically spend ``amount`` credits. Returns False if the balance was too low.

    Never blocks: the caller has already performed the (billable) hub call; a
    False return just means a concurrent use spent the last credit first.
    """
    updated = user.__class__.objects.filter(pk=user.pk, muses_credits__gte=amount).update(
        muses_credits=F("muses_credits") - amount
    )
    if updated:
        user.muses_credits = max(0, int(getattr(user, "muses_credits", 0)) - amount)
    return bool(updated)
