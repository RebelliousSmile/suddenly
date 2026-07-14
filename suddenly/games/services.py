"""
Game queryset services.

Shared queryset builders and business logic for the games domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.utils import timezone

from suddenly.characters.models import Character, CharacterAppearance, CharacterStatus

from .models import (
    CastRole,
    Game,
    GameCast,
    Rapport,
    RapportKind,
    RapportStatus,
    Report,
    ReportCast,
    ReportStatus,
)

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
      (``owner=user, status=pc``). Game-independent — a PC "peut intervenir dans
      n'importe quelle partie du réseau".
    - GM (``game.owner == user``): their own PCs ∪ the **NPCs of the game's cast**
      (``GameCast``). The casting — not ``origin_game`` — is what makes an NPC
      incarnable, so a GM can voice any NPC brought into their game.

    The server revalidates every submitted ``actor`` against this queryset, so a
    locked client chip is a convenience, not the enforcement.
    """
    owned_pcs = Q(owner=user, status=CharacterStatus.PC)
    if is_game_master(user, game):
        cast_npcs = Q(status=CharacterStatus.NPC, castings__game=game)
        return Character.objects.filter(owned_pcs | cast_npcs).distinct()
    return Character.objects.filter(owned_pcs)


def available_kinds(user: User, game: Game) -> list[tuple[str, Any]]:
    """The Rapport kinds the writer may pick in ``game``, given their role.

    ``narration`` **disappears** from the list for a non-GM — it is not greyed
    out, it is absent (composer rule 2c): narration *is* the GM's voice.
    ``closure`` is never here: the scene's compte rendu is written through the
    close flow, not composed as an ordinary post.
    """
    choices = [c for c in RapportKind.choices if c[0] != RapportKind.CLOSURE]
    if not is_game_master(user, game):
        choices = [c for c in choices if c[0] != RapportKind.NARRATION]
    return choices


def build_game_cast(game: Game) -> QuerySet[Character]:
    """The characters declared available in ``game`` (its ``GameCast``)."""
    return Character.objects.filter(castings__game=game).order_by("name")


def next_rapport_order(report: Report) -> int:
    """The order a new Rapport should take to append at the end of the scene."""
    from django.db.models import Max

    current = report.rapports.aggregate(m=Max("order"))["m"]
    return 0 if current is None else current + 1


def add_to_cast(game: Game, character: Character, user: User | None = None) -> GameCast:
    """Idempotently record that ``character`` is available in ``game``.

    Posting under a character in a game is what brings them into its cast — a PC
    may post in a game where it is not yet cast, and that very post enters it.
    """
    entry, _created = GameCast.objects.get_or_create(
        game=game, character=character, defaults={"added_by": user}
    )
    return entry


@transaction.atomic
def create_npc_in_cast(*, user: User, game: Game, name: str, description: str = "") -> Character:
    """Create a new NPC **and** add it to the game's cast, in one gesture.

    Backs the composer's "+ Nouveau PNJ": the ``Character`` and its ``GameCast``
    entry are born together (composer rule 2d), so the fresh NPC is immediately
    incarnable in the current game.
    """
    character = Character.objects.create(
        name=name,
        description=description,
        status=CharacterStatus.NPC,
        creator=user,
        origin_game=game,
    )
    GameCast.objects.create(game=game, character=character, added_by=user)
    return character


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
        order=next_rapport_order(report),
    )
    rapport.full_clean(exclude=["report"])
    rapport.save()
    # Voicing a character in a game brings them into its cast (rule 2d).
    if actor is not None:
        add_to_cast(report.game, actor, report.author)
    return rapport


@transaction.atomic
def open_new_scene(
    *,
    user: User,
    character: Character,
    kind: str,
    content: str,
    game: Game | None = None,
    actor: Character | None = None,
    status: str = RapportStatus.PUBLISHED,
) -> tuple[Report, Rapport]:
    """Open a new scene featuring a character, in one transaction.

    ``game`` defaults to ``character.origin_game`` but may be **any** game — a
    character "peut intervenir dans n'importe quelle partie du réseau" (rule 2b),
    so the composer's game selector is not filtered by the chosen character.

    Produces, atomically:
      - ``Report(game=game, author=user, status=draft, released_at=None)`` — a
        fresh scene behind a closed wall,
      - a first ``Rapport``,
      - ``ReportCast(character=character, role=MAIN)`` (scene-level cast),
      - ``GameCast(game, character)`` — the protagonist enters the game's cast.

    The character appearance is intentionally **not** materialised eagerly: it is
    born from ``ReportCast`` at publication time (``publish_report``), which
    keeps the temporal wall coherent — while the scene is still in play
    (unreleased) the appearance does not exist yet.
    """
    if game is None:
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
    # The opening post brings the protagonist (and any distinct actor) into the
    # game's cast — this very post is what enters them (rule 2d).
    add_to_cast(game, character, user)
    if actor is not None and actor.pk != character.pk:
        add_to_cast(game, actor, user)

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


# ---------------------------------------------------------------------------
# Scene lifecycle — draft → closed → released (SUD-V, scene-edit dock).
#
#   draft    : status=draft — the scene is in play, editable.
#   closed   : status=published, released_at=None — the compte rendu is ready,
#              behind the wall, nothing shared yet.
#   released : released_at set — the resolved account is public.
# ---------------------------------------------------------------------------


@transaction.atomic
def close_scene(
    *, report: Report, user: User, closure_content: str = "", release: bool = False
) -> Report:
    """Close a scene: optionally write its closure Rapport, publish it, and
    (optionally) cross the wall in one gesture.

    ``closure_content`` — when given, a ``closure`` Rapport (the scene's compte
    rendu) is appended, published. Publishing materialises the cast appearances
    (via :func:`publish_report`). ``release=True`` also sets ``released_at``.
    """
    if closure_content.strip():
        Rapport.objects.create(
            report=report,
            kind=RapportKind.CLOSURE,
            content=closure_content.strip(),
            status=RapportStatus.PUBLISHED,
            order=next_rapport_order(report),
        )

    if report.status != ReportStatus.PUBLISHED:
        publish_report(report, user)

    if release and report.released_at is None:
        report.released_at = timezone.now()
        report.save(update_fields=["released_at", "updated_at"])

    return report


def reopen_scene(*, report: Report) -> Report:
    """Reopen a closed scene back to draft (unshare + unpublish).

    Only allowed while the report is not both released *and* federated — once a
    released report has an ``ap_id``, the wall crossing is irreversible (mirrors
    ``report_release``); reopening such a report raises ``ValidationError``.
    """
    if report.released_at is not None and report.ap_id:
        raise ValidationError("A federated, released scene cannot be reopened.")
    report.status = ReportStatus.DRAFT
    report.released_at = None
    report.save(update_fields=["status", "released_at", "updated_at"])
    return report


@transaction.atomic
def move_rapport(*, report: Report, rapport: Rapport, direction: str) -> None:
    """Move a Rapport one step up/down in the scene sequence.

    Renumbers the whole scene to a dense 0..n ``order`` after the swap, so the
    sequence stays well-defined however posts were originally appended.
    """
    ordered = list(report.rapports.all())  # Meta ordering = [order, created_at]
    ids = [r.pk for r in ordered]
    if rapport.pk not in ids:
        return
    idx = ids.index(rapport.pk)
    swap = idx - 1 if direction == "up" else idx + 1
    if swap < 0 or swap >= len(ordered):
        return  # already at the edge — nothing to do
    ordered[idx], ordered[swap] = ordered[swap], ordered[idx]
    for position, item in enumerate(ordered):
        if item.order != position:
            item.order = position
            item.save(update_fields=["order", "updated_at"])
