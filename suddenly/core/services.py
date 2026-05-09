"""
Core service layer — shared business queries used by views.
"""

from __future__ import annotations

from typing import Any, cast

from django.core.cache import cache

from suddenly.games.models import Report, ReportStatus

EXPLORER_TAGS_TTL = 300
EXPLORER_SYSTEMS_TTL = 300
INSTANCE_STATS_TTL = 600
RECENT_REPORTS_TTL = 60

# Limits passed to get_recent_public_reports — every value must be listed here
# so cache_invalidation.invalidate_recent_public_reports can flush all keys.
# Adding a new caller with a non-default limit requires extending this tuple.
RECENT_REPORTS_LIMITS: tuple[int, ...] = (3,)


def get_recent_public_reports(limit: int = 3) -> list[Report]:
    cache_key = f"recent_public_reports:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(list[Report], cached)
    reports = list(
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility="public",
            remote=False,
        )
        .select_related("author", "game")
        .prefetch_related("cast", "quotes")
        .order_by("-published_at")[:limit]
    )
    cache.set(cache_key, reports, RECENT_REPORTS_TTL)
    return reports


def get_distinct_tag_names(model_cls: type[Any]) -> list[str]:
    cache_key = f"explorer_tags:{model_cls._meta.label_lower}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(list[str], cached)
    names = sorted(
        model_cls.objects.filter(remote=False, tags__isnull=False)
        .values_list("tags__name", flat=True)
        .distinct()
    )
    cache.set(cache_key, names, EXPLORER_TAGS_TTL)
    return names


def get_distinct_game_systems() -> list[str]:
    from suddenly.games.models import Game

    cache_key = "explorer_game_systems"
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(list[str], cached)
    names = sorted(
        Game.objects.filter(remote=False)
        .exclude(game_system="")
        .values_list("game_system", flat=True)
        .distinct()
    )
    cache.set(cache_key, names, EXPLORER_SYSTEMS_TTL)
    return names


def get_instance_stats() -> dict[str, int]:
    cache_key = "instance_stats"
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(dict[str, int], cached)

    from suddenly.activitypub.models import FederatedServer
    from suddenly.characters.models import Character
    from suddenly.users.models import User

    stats = {
        "users": User.objects.filter(is_active=True, remote=False).count(),
        "reports": Report.objects.filter(status=ReportStatus.PUBLISHED).count(),
        "characters": Character.objects.filter(remote=False).count(),
        "instances": FederatedServer.objects.exclude(status="BLOCKED").count(),
    }
    cache.set(cache_key, stats, INSTANCE_STATS_TTL)
    return stats
