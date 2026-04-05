"""
GM Dashboard views (DA-1, wireframe 12-gm-dashboard.md).

Shows the GM's NPCs, pending link requests, and recent activity.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import HttpRequest, HttpResponse

from suddenly.core.views import htmx_render

from .models import Character, CharacterStatus, LinkRequest, LinkRequestStatus


@login_required
def gm_dashboard(request: HttpRequest) -> HttpResponse:
    """GM Dashboard — overview of created NPCs and pending requests (US-14)."""
    user = request.user

    # NPCs with pending requests (prioritized)
    npcs_with_requests = (
        Character.objects.filter(creator=user, status=CharacterStatus.NPC)
        .prefetch_related(
            Prefetch(
                "link_requests_received",
                queryset=LinkRequest.objects.filter(
                    status__in=[LinkRequestStatus.PENDING, LinkRequestStatus.QUEUED]
                )
                .select_related("requester")
                .order_by("created_at"),
                to_attr="pending_requests",
            )
        )
        .annotate(
            pending_count=Count(
                "link_requests_received",
                filter=Q(
                    link_requests_received__status__in=[
                        LinkRequestStatus.PENDING,
                        LinkRequestStatus.QUEUED,
                    ]
                ),
            )
        )
        .filter(pending_count__gt=0)
        .order_by("-pending_count")
    )

    # All NPCs without pending requests
    npcs_available = (
        Character.objects.filter(creator=user, status=CharacterStatus.NPC)
        .annotate(
            pending_count=Count(
                "link_requests_received",
                filter=Q(
                    link_requests_received__status__in=[
                        LinkRequestStatus.PENDING,
                        LinkRequestStatus.QUEUED,
                    ]
                ),
            )
        )
        .filter(pending_count=0)
        .select_related("origin_game")
        .order_by("-created_at")[:12]
    )

    # Linked characters (accepted links)
    linked = (
        Character.objects.filter(creator=user)
        .exclude(status=CharacterStatus.NPC)
        .select_related("owner", "origin_game")
        .order_by("-updated_at")[:6]
    )

    # Stats
    total_npcs = Character.objects.filter(creator=user, status=CharacterStatus.NPC).count()
    total_requests = LinkRequest.objects.filter(
        target_character__creator=user,
        status__in=[LinkRequestStatus.PENDING, LinkRequestStatus.QUEUED],
    ).count()

    return htmx_render(
        request,
        full_template="characters/gm_dashboard.html",
        partial_template="characters/gm_dashboard.html",
        context={
            "npcs_with_requests": npcs_with_requests,
            "npcs_available": npcs_available,
            "linked": linked,
            "total_npcs": total_npcs,
            "total_requests": total_requests,
        },
    )
