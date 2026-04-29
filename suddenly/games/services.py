"""
Game queryset services.

Shared queryset builders for the games domain.
"""

from __future__ import annotations

from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.http import HttpRequest

from .models import Game


def build_game_queryset(request: HttpRequest) -> QuerySet[Game]:
    """Build filtered game queryset from request params."""
    public_filter = Q(is_public=True, remote=False)
    if request.user.is_authenticated:
        public_filter |= Q(owner=request.user, remote=False)

    qs = (
        Game.objects.filter(public_filter)
        .select_related("owner", "game_system_ref")
        .annotate(
            report_count=Count("reports", distinct=True),
            char_npc=Count("characters", filter=Q(characters__status="npc"), distinct=True),
            char_pc=Count("characters", filter=Q(characters__status="pc"), distinct=True),
            char_adopted=Count(
                "characters",
                filter=Q(characters__status__in=["claimed", "adopted"]),
                distinct=True,
            ),
            char_forked=Count("characters", filter=Q(characters__status="forked"), distinct=True),
        )
        .order_by("-updated_at")
    )

    system = request.GET.get("system", "").strip()
    if system:
        qs = qs.filter(
            Q(game_system_ref__name__icontains=system) | Q(game_system__icontains=system)
        )

    tag = request.GET.get("tag", "").strip()
    if tag:
        qs = qs.filter(tags__name=tag)

    return qs
