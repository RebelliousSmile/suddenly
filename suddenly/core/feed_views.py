"""
Feed views — 3 scopes (DA-1, wireframe 10-feed.md).

Abonnements: CRs from followed users/games
Instance: All public local content
Fediverse: Federated content from known instances
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render
from suddenly.games.models import Report, ReportStatus


def interleave_promos(reports: list[Any], npcs: list[Any], every: int) -> list[dict[str, Any]]:
    """Blend reports and claimable-NPC promocards into one ordered feed (SUD-P1).

    Produces a single ordered list of ``{"type": "report"|"promo", "obj": ...}``
    items rather than two disjoint blocks. A promocard is inserted after every
    ``every`` reports, consuming NPCs in order until they run out.

    Wireframe guarantee: if the feed is non-empty but shorter than ``every``
    (so no promo would otherwise be inserted), one promo is still appended at
    the end — as long as an NPC is available.
    """
    items: list[dict[str, Any]] = []
    if every < 1:
        every = 1
    npc_iter = iter(npcs)
    promos_inserted = 0

    for index, report in enumerate(reports, start=1):
        items.append({"type": "report", "obj": report})
        if index % every == 0:
            npc = next(npc_iter, None)
            if npc is not None:
                items.append({"type": "promo", "obj": npc})
                promos_inserted += 1

    # Guarantee at least one promo on a non-empty, short feed.
    if reports and promos_inserted == 0:
        npc = next(npc_iter, None)
        if npc is not None:
            items.append({"type": "promo", "obj": npc})

    return items


@login_required
def feed_home(request: AuthenticatedRequest) -> HttpResponse:
    """Feed — Abonnements tab (default). US-12, US-28."""
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Character, Follow
    from suddenly.games.models import Game
    from suddenly.users.models import User

    user = request.user

    # Followed IDs via ORM subqueries (Django evaluates lazily, no Python loop)
    user_ct_id = ContentType.objects.get_for_model(User).pk
    game_ct_id = ContentType.objects.get_for_model(Game).pk

    followed_user_ids = Follow.objects.filter(
        follower=user, content_type_id=user_ct_id
    ).values_list("object_id", flat=True)
    followed_game_ids = Follow.objects.filter(
        follower=user, content_type_id=game_ct_id
    ).values_list("object_id", flat=True)

    # Published reports from followed users/games
    reports = (
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility="public",
        )
        .filter(Q(author_id__in=followed_user_ids) | Q(game_id__in=followed_game_ids))
        .select_related("game", "author")
        .order_by("-published_at")[:20]
    )

    # Available NPCs in followed games — promocard pool for interleaving.
    npcs = (
        Character.objects.filter(
            status="npc",
            remote=False,
            origin_game_id__in=followed_game_ids,
        )
        .select_related("origin_game")
        .order_by("-created_at")[:6]
    )

    # Blend reports and claim/adopt/fork promocards into one ordered feed (SUD-P1).
    promo_every = getattr(settings, "FEED_PROMO_EVERY", 6)
    feed_items = interleave_promos(list(reports), list(npcs), promo_every)

    return htmx_render(
        request,
        full_template="feed/home.html",
        partial_template="feed/_feed_items.html",
        context={
            "feed_items": feed_items,
            "reports": reports,
            "npcs": npcs,
            "active_tab": "subscriptions",
            "is_empty": not Follow.objects.filter(follower=user).exists(),
        },
    )


def feed_instance(request: HttpRequest) -> HttpResponse:
    """Feed — Instance tab. All public local content."""
    reports = (
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility="public",
            remote=False,
        )
        .select_related("game", "author")
        .order_by("-published_at")[:20]
    )

    return htmx_render(
        request,
        full_template="feed/home.html",
        partial_template="feed/_feed_items.html",
        context={
            "reports": reports,
            "active_tab": "instance",
        },
    )


def feed_fediverse(request: HttpRequest) -> HttpResponse:
    """Feed — Fediverse tab. Federated content."""
    reports = (
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility="public",
            remote=True,
        )
        .select_related("game", "author")
        .order_by("-published_at")[:20]
    )

    return htmx_render(
        request,
        full_template="feed/home.html",
        partial_template="feed/_feed_items.html",
        context={
            "reports": reports,
            "active_tab": "fediverse",
        },
    )


@login_required
def recommend_report(request: HttpRequest) -> HttpResponse:
    """Recommend (boost) a report. US-28. HTMX POST."""
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    report_id = request.POST.get("report_id", "")
    report = Report.objects.filter(pk=report_id, status=ReportStatus.PUBLISHED).first()
    if not report:
        return JsonResponse({"error": "Report not found"}, status=404)

    # Queue AP Announce activity
    from suddenly.activitypub.signals import _safe_delay
    from suddenly.activitypub.tasks import send_announce_activity

    _safe_delay(send_announce_activity, str(request.user.pk), str(report.pk))

    # Return updated button (HTMX swap)
    return render(
        request,
        "feed/_recommend_button.html",
        {"report": report, "recommended": True},
    )


def explore(request: HttpRequest) -> HttpResponse:
    """Deprecated Explorer surface — redirects to Stories (SUD-V5).

    The v3 wireframe drops Explorer (a flat firehose of published reports,
    wall-blind) in favour of Stories, which only surfaces content that has
    crossed the liberation wall. This view is kept as a permanent redirect so
    existing links do not 404.
    """
    from django.shortcuts import redirect

    return redirect("games:stories", permanent=True)
