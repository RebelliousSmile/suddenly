"""
Game queryset services.

Shared queryset builders for the games domain.
"""

from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.db.models import Count, Q
from django.db.models.query import QuerySet

from .models import Game


def build_game_queryset(
    user: AbstractBaseUser | AnonymousUser,
    q: str = "",
    system: str = "",
    tag: str = "",
) -> QuerySet[Game]:
    """Build filtered game queryset from explicit params."""
    public_filter = Q(is_public=True, remote=False)
    if user.is_authenticated:
        public_filter |= Q(owner=user, remote=False)

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

    if system.strip():
        qs = qs.filter(
            Q(game_system_ref__name__icontains=system.strip())
            | Q(game_system__icontains=system.strip())
        )

    if tag.strip():
        qs = qs.filter(tags__name=tag.strip())

    return qs
