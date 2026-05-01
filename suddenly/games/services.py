"""
Game queryset services.

Shared queryset builders and business logic for the games domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.utils import timezone

from suddenly.characters.models import Character, CharacterAppearance

from .models import Game, Report, ReportStatus

if TYPE_CHECKING:
    from suddenly.users.models import User


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


@transaction.atomic
def publish_report(report: Report, user: User) -> Report:
    """
    Publish a draft report.

    Iterates cast entries, creates NPCs for new characters, records
    CharacterAppearance for each resolved character, then marks the
    report as published.

    Returns the updated report instance.
    """
    for cast_entry in report.cast.select_related("character"):
        character: Character | None = cast_entry.character

        if cast_entry.is_new_character():
            character = Character.objects.create(
                name=cast_entry.new_character_name,
                description=cast_entry.new_character_description,
                status="npc",
                creator=user,
                origin_game=report.game,
            )

        if character is not None:
            CharacterAppearance.objects.get_or_create(
                character=character,
                report=report,
                defaults={"role": cast_entry.role},
            )

    report.status = ReportStatus.PUBLISHED
    report.published_at = timezone.now()
    report.save(update_fields=["status", "published_at", "updated_at"])

    return report
