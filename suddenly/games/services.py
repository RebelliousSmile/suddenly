"""
Game queryset services.

Shared queryset builders and business logic for the games domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.utils import timezone

from suddenly.characters.models import Character, CharacterAppearance, CharacterStatus

from .models import CastRole, Game, Rapport, RapportStatus, Report, ReportCast, ReportStatus

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
        .select_related("owner")
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
        qs = qs.filter(game_system__icontains=system.strip())

    if tag.strip():
        qs = qs.filter(tags__name=tag.strip())

    return qs


# ---------------------------------------------------------------------------
# Post composer (Rapport) — role-scoped actor viviers and creation gestures.
#
# The composer writes a single Rapport (a post) into a scene, unlike
# ``report_compose`` which writes a whole Report. Its context is frozen server
# side: (pc, game, role). The role is *deduced*, never trusted from the client:
#   is_gm = (game.owner == user).
# ---------------------------------------------------------------------------


def is_game_master(user: User, game: Game) -> bool:
    """Deduce the writer's role for a game. GM ⟺ they own the game.

    This is the authoritative role signal for the composer — the client never
    sends the role. Mirrors the ``is_owner`` check used in ``game_detail``.
    """
    return game.owner_id == user.pk


def build_actor_pool(user: User, game: Game) -> QuerySet[Character]:
    """Characters the user may make speak (``actor``) in ``game``, by role.

    - Player (``game.owner != user``): their own PCs only
      (``owner=user, status=pc``).
    - GM (``game.owner == user``): their own PCs ∪ the NPCs of the games they
      own (``status=npc, origin_game__owner=user``).

    The server revalidates every submitted ``actor`` against this queryset, so a
    locked client chip is a convenience, not the enforcement.
    """
    owned_pcs = Q(owner=user, status=CharacterStatus.PC)
    if is_game_master(user, game):
        owned_npcs = Q(status=CharacterStatus.NPC, origin_game__owner=user)
        return Character.objects.filter(owned_pcs | owned_npcs)
    return Character.objects.filter(owned_pcs)


def validate_actor_for_role(user: User, game: Game, actor: Character | None) -> None:
    """Raise ``ValidationError`` if ``actor`` is outside the user's role vivier.

    ``None`` is always allowed here (the ``actor``⟺``discussion`` rule is
    enforced separately by ``Rapport.clean``); a non-null actor must belong to
    :func:`build_actor_pool`.
    """
    if actor is None:
        return
    if not build_actor_pool(user, game).filter(pk=actor.pk).exists():
        raise ValidationError({"actor": "This actor is not one you may make speak in this game."})


def create_scene_post(
    *,
    report: Report,
    kind: str,
    content: str,
    actor: Character | None = None,
    status: str = RapportStatus.PUBLISHED,
) -> Rapport:
    """Create one Rapport inside an existing scene (``report``).

    The caller is responsible for the frozen context (``report`` and its author
    come from the server, never the payload). ``actor`` is revalidated against
    the writer's role vivier; ``Rapport.clean`` enforces the actor⟺discussion
    rule. Returns the saved Rapport.
    """
    validate_actor_for_role(report.author, report.game, actor)
    rapport = Rapport(
        report=report,
        kind=kind,
        content=content,
        actor=actor,
        status=status,
    )
    rapport.full_clean(exclude=["report"])
    rapport.save()
    return rapport


@transaction.atomic
def open_new_scene(
    *,
    user: User,
    character: Character,
    kind: str,
    content: str,
    actor: Character | None = None,
    status: str = RapportStatus.PUBLISHED,
) -> tuple[Report, Rapport]:
    """Open a new scene featuring a PC, in one transaction.

    Produces, atomically:
      - ``Report(game=character.origin_game, author=user, status=draft,
        released_at=None)`` — a fresh scene behind a closed wall,
      - a first ``Rapport``,
      - ``ReportCast(character=character, role=MAIN)``.

    The character appearance is intentionally **not** materialised eagerly: it is
    born from ``ReportCast`` at publication time (``publish_report``), which
    keeps the temporal wall coherent — while the scene is still in play
    (unreleased) the appearance does not exist yet.
    """
    game = character.origin_game

    # The protagonist must be a character the user may act as in this game.
    if not build_actor_pool(user, game).filter(pk=character.pk).exists():
        raise ValidationError({"character": "You cannot open a scene featuring this character."})

    validate_actor_for_role(user, game, actor)

    report = Report.objects.create(
        game=game,
        author=user,
        content="",
        status=ReportStatus.DRAFT,
        released_at=None,
    )

    rapport = Rapport(
        report=report,
        kind=kind,
        content=content,
        actor=actor,
        status=status,
    )
    rapport.full_clean(exclude=["report"])
    rapport.save()

    ReportCast.objects.create(
        report=report,
        character=character,
        role=CastRole.MAIN,
    )

    return report, rapport


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
