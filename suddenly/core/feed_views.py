"""
Feed views — 3 scopes (DA-1, wireframe 10-feed.md).

Abonnements: CRs from followed users/games
Instance: All public local content
Fediverse: Federated content from known instances
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render
from suddenly.games.models import Report, ReportStatus, ReportVisibility


@login_required
def feed_home(request: AuthenticatedRequest) -> HttpResponse:
    """Feed — Abonnements tab (default). US-12, US-28."""
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Prefetch

    from suddenly.characters.models import Character, Follow
    from suddenly.games.models import Game, Rapport
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

    # Published reports (scenes) from followed users/games. For the Friends tab
    # (Front #9) we read them as a stream of interventions grouped by scene, so
    # prefetch each scene's rapports (in reading order) to avoid N+1.
    reports = (
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility="public",
        )
        .filter(Q(author_id__in=followed_user_ids) | Q(game_id__in=followed_game_ids))
        .select_related("game", "author")
        .prefetch_related(
            Prefetch(
                "rapports",
                queryset=Rapport.objects.select_related("actor").order_by("created_at"),
            )
        )
        .order_by("-published_at")[:20]
    )

    # Available NPCs in followed games
    npcs = (
        Character.objects.filter(
            status="npc",
            remote=False,
            origin_game_id__in=followed_game_ids,
        )
        .select_related("origin_game")
        .order_by("-created_at")[:6]
    )

    return htmx_render(
        request,
        full_template="feed/home.html",
        partial_template="feed/_feed_items.html",
        context={
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
    """Community explore page — public reports, filterable, no login required."""
    language = request.GET.get("language", "")
    tag = request.GET.get("tag", "")

    qs = (
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility=ReportVisibility.PUBLIC,
            remote=False,
        )
        .select_related("game", "author")
        .order_by("-published_at")
    )

    if language:
        qs = qs.filter(language=language)
    if tag:
        qs = qs.filter(tags__name=tag)

    all_tags: list[str] = sorted(
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility=ReportVisibility.PUBLIC,
            remote=False,
            tags__isnull=False,
        )
        .values_list("tags__name", flat=True)
        .distinct()
    )

    return htmx_render(
        request,
        full_template="explore/explore.html",
        partial_template="explore/_results.html",
        context={
            "reports": qs[:30],
            "active_language": language,
            "active_tag": tag,
            "all_tags": all_tags,
            "languages": settings.LANGUAGES,
        },
    )
