"""
Core service layer — shared business queries used by views.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.core.cache import cache

from suddenly.games.models import Report, ReportStatus

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django.core.paginator import Page

    from suddenly.users.models import User

POPULAR_SCENES_PER_PAGE = 20

EXPLORER_TAGS_TTL = 300
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
        .prefetch_related("cast")
        .order_by("-published_at")[:limit]
    )
    cache.set(cache_key, reports, RECENT_REPORTS_TTL)
    return reports


def popular_scenes_page(
    page_number: str | int | None, *, user: User | AnonymousUser
) -> Page[Report]:
    """One page of the most-liked released scenes (#146), ready for the wall.

    Ranking lives in ``Report.objects.most_liked()`` (wall filter + like count +
    ``like_count >= 1``); this only adds the per-card fetch shape. ``rapports``
    are prefetched (the scene card reads them) and ``liked``/``recommended`` are
    annotated only for an authenticated visitor via ``annotate_viewer_reactions``
    — anonymous cards read a falsy ``report.liked``/``report.recommended``.
    """
    from django.core.paginator import Paginator
    from django.db.models import Prefetch

    from suddenly.games.models import Rapport
    from suddenly.games.services import annotate_viewer_reactions

    qs = (
        Report.objects.most_liked()
        .select_related("game", "author")
        .prefetch_related(
            Prefetch(
                "rapports",
                queryset=Rapport.objects.select_related("actor").order_by("created_at"),
            )
        )
    )
    annotated = annotate_viewer_reactions(qs, user)
    return Paginator(annotated, POPULAR_SCENES_PER_PAGE).get_page(page_number)


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
