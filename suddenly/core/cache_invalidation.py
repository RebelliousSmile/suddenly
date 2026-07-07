"""
Centralized cache invalidation handlers for service-layer caches in core/services.py.

Wired in apps.CoreConfig.ready() with explicit dispatch_uid to survive --reuse-db
and dev autoreload (handlers stay connected across reloads — duplicates without uid).
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache

_M2M_ACTIONS = {"post_add", "post_remove", "post_clear"}


def invalidate_explorer_tags_character(
    sender: Any, action: str | None = None, **kwargs: Any
) -> None:
    if action is not None and action not in _M2M_ACTIONS:
        return
    from suddenly.characters.models import Character

    cache.delete(f"explorer_tags:{Character._meta.label_lower}")


def invalidate_explorer_tags_game(sender: Any, action: str | None = None, **kwargs: Any) -> None:
    if action is not None and action not in _M2M_ACTIONS:
        return
    from suddenly.games.models import Game

    cache.delete(f"explorer_tags:{Game._meta.label_lower}")


def invalidate_recent_public_reports(sender: Any, **kwargs: Any) -> None:
    from suddenly.core.services import RECENT_REPORTS_LIMITS

    cache.delete_many([f"recent_public_reports:{n}" for n in RECENT_REPORTS_LIMITS])


def invalidate_instance_stats(sender: Any, **kwargs: Any) -> None:
    cache.delete("instance_stats")
