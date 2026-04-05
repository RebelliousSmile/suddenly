"""
Feed views — 3 scopes (DA-1, wireframe 10-feed.md).

Abonnements: CRs from followed users/games
Instance: All public local content
Fediverse: Federated content from known instances
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse

from suddenly.core.views import htmx_render
from suddenly.games.models import Report, ReportStatus


@login_required
def feed_home(request: HttpRequest) -> HttpResponse:
    """Feed — Abonnements tab (default). US-12, US-28."""
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Character, Follow
    from suddenly.games.models import Game
    from suddenly.users.models import User

    user = request.user

    # Collect followed IDs by type
    follows = Follow.objects.filter(follower=user).values("content_type_id", "object_id")

    user_ct = ContentType.objects.get_for_model(User)
    game_ct = ContentType.objects.get_for_model(Game)

    followed_user_ids = [f["object_id"] for f in follows if f["content_type_id"] == user_ct.pk]
    followed_game_ids = [f["object_id"] for f in follows if f["content_type_id"] == game_ct.pk]

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
            "is_empty": not followed_user_ids and not followed_game_ids,
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
