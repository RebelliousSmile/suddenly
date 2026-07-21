"""
Game queryset services.

Shared queryset builders and business logic for the games domain.
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from typing import TYPE_CHECKING, Any, cast

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Q
from django.db.models.query import QuerySet
from django.utils import timezone

from suddenly.characters.models import (
    AppearanceRole,
    Character,
    CharacterAppearance,
    CharacterStatus,
)
from suddenly.characters.services import build_owned_pc_queryset

from .models import (
    CastRole,
    Game,
    GameCast,
    Like,
    MarkerKind,
    Rapport,
    RapportKind,
    RapportLink,
    RapportMarker,
    RapportMedia,
    RapportStatus,
    Recommendation,
    Report,
    ReportCast,
    ReportStatus,
    ReportTemporalKind,
)

if TYPE_CHECKING:
    from suddenly.users.models import User


def build_game_queryset(
    user: AbstractBaseUser | AnonymousUser,
    q: str = "",
    system: str = "",
    tag: str = "",
    character: Character | None = None,
) -> QuerySet[Game]:
    """Build filtered game queryset from explicit params.

    ``character`` — when given, restricts to games the character can act in:
    its origin game, plus any game it has already been cast into (``GameCast``).
    """
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
            # A fork is a PC with a parent (no dedicated status); count by lineage.
            char_forked=Count(
                "characters", filter=Q(characters__parent__isnull=False), distinct=True
            ),
        )
        .order_by("-updated_at")
    )

    if system.strip():
        qs = qs.filter(game_system__icontains=system.strip())

    if tag.strip():
        qs = qs.filter(tags__name=tag.strip())

    if character is not None:
        qs = qs.filter(Q(pk=character.origin_game_id) | Q(cast__character=character)).distinct()

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


def can_edit_scene(user: AbstractBaseUser | AnonymousUser, report: Report) -> bool:
    """Who may edit a scene: its author or the game's GM (owner).

    The single authority for scene-editing rights (decision: author OR
    game.owner). Also gates who reads a scene still behind the wall — an editor
    sees their in-progress scene, everyone else waits for release. Mirrors
    ``is_game_master`` (``game.owner_id``) but takes the possibly-anonymous
    ``request.user`` directly. Accessing ``report.game`` costs one query when it
    is not already loaded; callers on hot paths select_related it.
    """
    if not user.is_authenticated:
        return False
    return bool(report.author_id == user.pk or report.game.owner_id == user.pk)


def annotate_viewer_reactions(
    qs: QuerySet[Report], user: AbstractBaseUser | AnonymousUser
) -> QuerySet[Report]:
    """Annotate per-viewer ``liked`` (#138) and ``recommended`` (#155) on a Report qs.

    Single source of truth for both engagement flags — replaces the duplicated
    ``liked=Exists(...)`` annotation across every feed queryset. Anonymous viewer
    → qs unchanged (templates read a falsy ``report.liked`` / ``report.recommended``).
    Set-based ``Exists`` subqueries: one correlated JOIN per flag for the whole
    page, never a query per card.
    """
    if not user.is_authenticated:
        return qs
    concrete = cast("User", user)
    return qs.annotate(
        liked=Exists(Like.objects.filter(report=OuterRef("pk"), user=concrete)),
        recommended=Exists(Recommendation.objects.filter(report=OuterRef("pk"), user=concrete)),
    )


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
    owned_pcs = build_owned_pc_queryset(user)
    if is_game_master(user, game):
        cast_npcs = Character.objects.filter(status=CharacterStatus.NPC, castings__game=game)
        return (owned_pcs | cast_npcs).distinct()
    return owned_pcs


def build_protagonist_pool(user: User) -> QuerySet[Character]:
    """Characters the user may feature as the protagonist of a *new* scene.

    Game-independent union of :func:`build_actor_pool` across every game the user
    could open a scene in:

    - their own PCs (``owner=user, status=pc``) — actable in any game;
    - NPCs cast into a game they master (``status=npc`` &
      ``castings__game__owner=user``) — actable as GM of that game.

    This is what the free-mode "Personnage" picker must offer: every character it
    lists is a valid protagonist for at least one game the composer will let the
    user pick, so ``open_new_scene``'s per-game ``build_actor_pool`` re-check
    never rejects a legitimately-offered choice. A character merely *created*
    (not owned) by the user, or owned but not ``pc`` (adopted, claimed, forked),
    is deliberately excluded — it cannot open a scene.

    A character with **no writable game at all** is also excluded (shouldn't
    happen — a PC is born in a game — but a null ``origin_game`` with no casting
    would otherwise be offered only to hit an empty partie list). "Writable game"
    mirrors :func:`build_game_queryset` exactly: visible to the user (public &
    non-remote, or owned) — as the character's origin game or a game it is cast
    into. Mastered NPCs are always cast into a game the user owns, so that leg
    already guarantees one.
    """
    visible_games = Game.objects.filter(
        Q(is_public=True, remote=False) | Q(owner=user, remote=False)
    ).values("pk")
    own_playable_pcs = build_owned_pc_queryset(user).filter(
        Q(origin_game__in=visible_games) | Q(castings__game__in=visible_games)
    )
    mastered_npcs = Character.objects.filter(status=CharacterStatus.NPC, castings__game__owner=user)
    return (own_playable_pcs | mastered_npcs).distinct()


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


def build_composer_context(
    user: User,
    *,
    report: Report | None = None,
    game: Game | None = None,
    character: Character | None = None,
    selected_actor: str = "",
    selected_actor_label: str = "",
    edit_rapport: Rapport | None = None,
) -> dict[str, object]:
    """Build the single source of truth the ``_composer.html`` partial consumes.

    Frozen mode (``report`` given): game, personnage and language are inherited
    from the scene — the header is a breadcrumb. Free mode (``report`` absent):
    the header is two selectors and the caller supplies ``games``/``personnages``.

    Either way the role-scoped, non-negotiable pieces are computed here:
    ``is_gm`` (deduced), ``kinds`` (narration only for a GM) and the actor pool.
    """
    frozen = report is not None
    if frozen and report is not None:
        game = report.game

    # Edit mode: the sidebar composer reopens hydrated on an existing post
    # (kind/body via the template, actor chip preselected here).
    if edit_rapport is not None and edit_rapport.actor is not None:
        selected_actor = edit_rapport.actor.slug
        selected_actor_label = edit_rapport.actor.name

    if game is not None:
        is_gm = is_game_master(user, game)
        kinds = available_kinds(user, game)
        actors = build_actor_pool(user, game).select_related("origin_game").order_by("name")
        cast_npcs = build_game_cast(game).filter(status=CharacterStatus.NPC)
    else:
        is_gm = False
        kinds = []
        actors = Character.objects.none()
        cast_npcs = Character.objects.none()

    own_pcs = build_owned_pc_queryset(user).order_by("name")

    # Reply targets (discussion) — the scene's own posts. Only in frozen mode:
    # from the feed there is no scene yet to reply within.
    reply_targets = (
        report.rapports.select_related("actor").order_by("order", "created_at")
        if report is not None
        else Rapport.objects.none()
    )

    # Rule 2a: nothing leaves without a personnage AND a partie — drafts too.
    # In frozen mode both are inherited from the scene, so sending is allowed.
    can_send = frozen or (game is not None and character is not None)

    # Free mode only: preview the game's last published scene (D1=B) below the
    # composer, with a link that opens the editor when the viewer authored it,
    # or the read view otherwise (D2). Absent in frozen mode and without a game.
    last_scene: Report | None = None
    last_scene_rapports: list[Rapport] = []
    last_scene_can_edit = False
    if not frozen and game is not None:
        last_scene = latest_published_scene(game)
        if last_scene is not None:
            last_scene_rapports = latest_scene_rapports(last_scene)
            last_scene_can_edit = last_scene.author_id == user.id

    return {
        "report": report,
        "frozen": frozen,
        "game": game,
        "is_gm": is_gm,
        "kinds": kinds,
        "actors": actors,
        "cast_npcs": cast_npcs,
        "own_pcs": own_pcs,
        "reply_targets": reply_targets,
        "selected_character": character,
        "selected_actor": selected_actor,
        "selected_actor_label": selected_actor_label,
        "can_send": can_send,
        "last_scene": last_scene,
        "last_scene_rapports": last_scene_rapports,
        "last_scene_can_edit": last_scene_can_edit,
        "edit_rapport": edit_rapport,
    }


def latest_published_scene(game: Game) -> Report | None:
    """The game's most recently published scene, any author (composer D1=B).

    Read-only narrative context for the free-mode composer: the last scene the
    network has seen in this game, newest first. Draft scenes stay invisible.
    """
    return (
        game.reports.filter(status=ReportStatus.PUBLISHED)
        .select_related("author", "game")
        .order_by(F("published_at").desc(nulls_last=True), "-created_at")
        .first()
    )


def latest_scene_rapports(report: Report, limit: int = 3) -> list[Rapport]:
    """The scene's last published posts, newest first, bounded (compact preview)."""
    return list(
        report.rapports.filter(status=RapportStatus.PUBLISHED)
        .select_related("actor")
        .order_by("-order", "-created_at")[:limit]
    )


def build_composer_feed_context(
    user: User,
    *,
    game: Game | None = None,
    character: Character | None = None,
) -> dict[str, object]:
    """Free-mode composer context: adds the game/personnage pickers to the base context.

    Used both by the standalone ``games:composer`` page (which recomputes role-scoped
    context as the writer picks a game/personnage) and by the feed sidebar (initial,
    unselected state — called with no ``game``/``character``).

    ``games`` is scoped to ``character`` once one is picked (rule 2b): its origin
    game plus any game it has already been cast into.
    """
    ctx = build_composer_context(user, game=game, character=character)
    ctx["games"] = build_game_queryset(user, character=character)
    ctx["personnages"] = build_protagonist_pool(user).select_related("origin_game").order_by("name")
    return ctx


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


def _attach_rapport_media(
    rapport: Rapport, kind: str, image: object | None, media_alt: str
) -> None:
    """One image, description only (``RapportMedia.clean`` also enforces this)."""
    if image is not None and kind == RapportKind.DESCRIPTION:
        media = RapportMedia(
            rapport=rapport,
            image=image,
            alt=(media_alt or "").strip(),
        )
        media.full_clean()
        media.save()


@transaction.atomic
def create_scene_post(
    *,
    report: Report,
    kind: str,
    content: str,
    actor: Character | None = None,
    status: str = RapportStatus.PUBLISHED,
    reply_parent: Rapport | None = None,
    reply_iri: str = "",
    image: object | None = None,
    media_alt: str = "",
) -> Rapport:
    """Create one Rapport inside an existing scene (``report``).

    The caller is responsible for the frozen context (``report`` and its author
    come from the server, never the payload). ``actor`` is revalidated against
    the writer's role vivier; ``Rapport.clean`` enforces the actor⟺discussion
    rule.

    ``reply_parent`` / ``reply_iri`` — an optional reply target (a Rapport of the
    same scene, or a federated IRI). At most one is used (local wins); it becomes
    a ``RapportLink``. Returns the saved Rapport.
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

    reply_iri = (reply_iri or "").strip()
    if reply_parent is not None or reply_iri:
        link = RapportLink(
            rapport=rapport,
            parent_rapport=reply_parent,
            parent_iri=(reply_iri or None) if reply_parent is None else None,
        )
        link.full_clean(exclude=["rapport"])
        link.save()

    _attach_rapport_media(rapport, kind, image, media_alt)
    return rapport


@transaction.atomic
def update_scene_post(
    *,
    rapport: Rapport,
    kind: str,
    content: str,
    actor: Character | None = None,
) -> Rapport:
    """Edit one Rapport in place — the composer's edit mode.

    Mirrors :func:`create_scene_post`'s validation: ``actor`` is revalidated
    against the writer's role vivier and ``Rapport.clean`` enforces the
    actor⟺kind rule. Sequence position, status, media and reply links are NOT
    touched here — they have their own endpoints.
    """
    report = rapport.report
    validate_actor_for_role(report.author, report.game, actor)
    rapport.kind = kind
    rapport.content = content
    rapport.actor = actor
    rapport.full_clean(exclude=["report"])
    rapport.save(update_fields=["kind", "content", "actor", "updated_at"])
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
    image: object | None = None,
    media_alt: str = "",
) -> tuple[Report, Rapport]:
    """Open a new scene featuring a character, in one transaction.

    ``game`` defaults to ``character.origin_game`` but may be any game the
    character is allowed to act in per ``build_actor_pool`` (rule 2b) — the
    composer's free-mode game picker further restricts choices to the
    character's origin game plus games it is already cast into, but this
    function itself does not enforce that narrower UI-level restriction.

    ``image``/``media_alt`` attach a ``RapportMedia`` when ``kind`` is
    ``description`` (see ``_attach_rapport_media``).

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

    _attach_rapport_media(rapport, kind, image, media_alt)

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


def record_appearance_from_marker(marker: RapportMarker) -> CharacterAppearance | None:
    """A ``CHARACTER_APPEARS`` marker records the character's presence in the scene.

    Bridges the narrative layer (entrance/exit markers) to the model layer
    (:class:`CharacterAppearance`), so "make an existing NPC enter the scene"
    produces the same durable presence record as a cast-driven publication.

    Idempotent: appearance is unique per ``(character, report)`` — an existing
    entry (e.g. a ``MAIN`` role from publication) is left untouched. Only
    ``CHARACTER_APPEARS`` records; ``CHARACTER_LEAVES`` does not remove the
    appearance — appearing in a scene is a durable fact, orthogonal to the
    character having since left. Returns the appearance, or ``None`` when the
    marker is not a character entrance.
    """
    if marker.kind != MarkerKind.CHARACTER_APPEARS or marker.character is None:
        return None
    appearance, _ = CharacterAppearance.objects.get_or_create(
        character=marker.character,
        report=marker.rapport.report,
        defaults={"role": AppearanceRole.SUPPORTING},
    )
    return appearance


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
def close_game(*, game: Game, user: User) -> Game:
    """Close a game: the GM-only, terminal lifecycle action (DEC-D7, Epic D #134).

    Idempotent — closing an already-closed game is a no-op, not an error, so a
    network retry or double click is harmless. Once ``completed_at`` is set,
    every report of this game is treated as released regardless of its own
    ``released_at`` (``wall_open_q()``), and the cast auto-follows are
    recomputed: any AUTO follow only justified by this game's membership stops
    being justified the moment the game is no longer active (see
    ``active_comembership_exists`` in ``games/cast_follow.py``) — a game
    closure is teardown's other trigger besides a cast entry removal.
    """
    if not is_game_master(user, game):
        raise PermissionDenied("Only the game's GM can close it.")
    if game.completed_at is not None:
        return game

    game.completed_at = timezone.now()
    game.save(update_fields=["completed_at", "updated_at"])

    from suddenly.games.cast_follow import teardown_cast_follows_for_game

    teardown_cast_follows_for_game(game)
    return game


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


# ---------------------------------------------------------------------------
# Game system labels — free-form text, no catalogue.
#
# Two services back the create/edit form:
#   - ``known_game_systems`` feeds the top-N suggestion pills (most-used first).
#   - ``near_duplicate_system`` guards against near-duplicate labels
#     ("L'appel de cthulhu" vs "Appel de Cthulhu") — the metric is mirrored
#     client-side in the ``gameForm`` Alpine component (frontend/src/main.js).
# ---------------------------------------------------------------------------

_SYSTEM_NEAR_DUP_THRESHOLD = 0.84
_KNOWN_SYSTEMS_CAP = 500


def known_game_systems(limit: int = _KNOWN_SYSTEMS_CAP) -> list[str]:
    """Distinct non-empty game_system labels, most-used first (instance-wide)."""
    rows = (
        Game.objects.exclude(game_system="")
        .values("game_system")
        .annotate(n=Count("id"))
        .order_by("-n", "game_system")[:limit]
    )
    return [row["game_system"] for row in rows]


def normalize_system(label: str) -> str:
    """Comparison key: accent-stripped, lowercased, punctuation → space, collapsed."""
    decomposed = unicodedata.normalize("NFD", label)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", stripped.lower()).split())


def _similarity(a: str, b: str) -> float:
    """Normalized Levenshtein ratio in [0, 1]. Mirrored in gameForm (main.js)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        cur = [i]
        for j, char_b in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (char_a != char_b)))
        prev = cur
    return 1.0 - prev[-1] / max(len(a), len(b))


def near_duplicate_system(
    entered: str, known: list[str], threshold: float = _SYSTEM_NEAR_DUP_THRESHOLD
) -> str | None:
    """Closest known label if ``entered`` is a near-duplicate (but not an exact match)."""
    entered = entered.strip()
    if not entered or entered in known:
        return None
    entered_key = normalize_system(entered)
    if not entered_key:
        return None
    best: str | None = None
    best_ratio = 0.0
    for label in known:
        ratio = _similarity(entered_key, normalize_system(label))
        if ratio > best_ratio:
            best, best_ratio = label, ratio
    return best if best_ratio >= threshold else None


# ---------------------------------------------------------------------------
# Fiction order — reading chain (previous_report) + chronology (temporal_*).
#
# The fiction order is explicit and distinct from Meta.ordering
# (session_date / published_at / created_at). Source of truth: the self-FK
# ``previous_report``. It is a forest (branching allowed), not a total order —
# so it lives ONLY here, never in a manager or Meta.ordering. All the logic the
# model must not hold (invariants, reading, mutation) is in this section.
# ---------------------------------------------------------------------------

# Guard against a cycle in corrupted pre-constraint data: bound the upward walk.
_MAX_FICTION_CHAIN_DEPTH = 10_000


def validate_fiction_links(report: Report) -> None:
    """Validate the fiction-order invariants on ``report``; raise ``ValidationError``.

    Kept in the service (never the model) so it can be reused from ``clean``/forms.
    ``temporal_anchor`` is NOT traversed by :func:`fiction_thread`, so a deep anchor
    cycle is never fatal to rendering — only anchor self-reference is blocked here
    (deep anchor cycles are data hygiene, out of the hard-invariant scope).
    """
    # 1. No self-reference on either axis.
    if report.previous_report_id is not None and report.previous_report_id == report.pk:
        raise ValidationError({"previous_report": "A report cannot precede itself."})
    if report.temporal_anchor_id is not None and report.temporal_anchor_id == report.pk:
        raise ValidationError({"temporal_anchor": "A report cannot anchor to itself."})

    # 2. XOR local/remote — app-level echo of the CheckConstraint, with a message.
    if report.previous_report_id is not None and report.previous_report_iri:
        raise ValidationError(
            {"previous_report_iri": "Set either previous_report or previous_report_iri, not both."}
        )
    if report.temporal_anchor_id is not None and report.temporal_anchor_iri:
        raise ValidationError(
            {"temporal_anchor_iri": "Set either temporal_anchor or temporal_anchor_iri, not both."}
        )

    # 3. Same game on both local axes.
    previous = report.previous_report
    if previous is not None and previous.game_id != report.game_id:
        raise ValidationError(
            {"previous_report": "The previous report must belong to the same game."}
        )
    anchor = report.temporal_anchor
    if anchor is not None and anchor.game_id != report.game_id:
        raise ValidationError(
            {"temporal_anchor": "The temporal anchor must belong to the same game."}
        )

    # 4. temporal_kind NORMAL ⟺ no anchor and no label (bidirectional).
    has_anchor = report.temporal_anchor_id is not None or bool(report.temporal_anchor_iri)
    has_label = bool(report.temporal_label)
    if report.temporal_kind == ReportTemporalKind.NORMAL and (has_anchor or has_label):
        raise ValidationError(
            {"temporal_kind": "A normal scene carries no temporal anchor or label."}
        )

    # 5. No cycle in the previous_report chain (bounded upward walk).
    if report.previous_report_id is not None:
        seen: set[Any] = {report.pk}
        current: Report | None = report.previous_report
        depth = 0
        while current is not None:
            depth += 1
            if depth > _MAX_FICTION_CHAIN_DEPTH:
                raise ValidationError(
                    {"previous_report": "The fiction chain is too deep (possible cycle)."}
                )
            if current.pk in seen:
                raise ValidationError(
                    {"previous_report": "This link would create a cycle in the fiction order."}
                )
            seen.add(current.pk)
            current = current.previous_report


def _fiction_sort_key(report: Report) -> tuple[int, bool, datetime.date, datetime.datetime]:
    """Order siblings mainline-first: branch_order, then session_date (nulls last),
    then created_at."""
    return (
        report.branch_order,
        report.session_date is None,
        report.session_date or datetime.date.min,
        report.created_at,
    )


def fiction_thread(game: Game) -> list[Report]:
    """Return ``game``'s reports in fiction (reading) order, mainline-first.

    Roots = reports with no predecessor at all (``previous_report`` AND
    ``previous_report_iri`` both null). Children are visited depth-first, sorted by
    :func:`_fiction_sort_key`, so the mainline comes first and branches follow.
    Flashbacks/flashforwards appear at their chain position (they carry a
    ``previous_report``), exposed via ``temporal_kind`` / ``temporal_label``.

    The whole forest is loaded in a bounded number of queries
    (``select_related("author")`` + ``prefetch_related("next_reports")``); the
    adjacency is then built in memory from ``previous_report_id`` and walked with a
    DFS — so the query cost is independent of the tree depth or size. Building the
    adjacency from the flat list (not the reverse relation) keeps every visited node
    a single, prefetched instance, avoiding an N+1 on ``next_reports``.
    """
    reports = list(game.reports.select_related("author").prefetch_related("next_reports"))

    children: dict[Any, list[Report]] = {}
    roots: list[Report] = []
    for report in reports:
        if report.previous_report_id is None and not report.previous_report_iri:
            roots.append(report)
        if report.previous_report_id is not None:
            children.setdefault(report.previous_report_id, []).append(report)

    roots.sort(key=_fiction_sort_key)

    ordered: list[Report] = []
    visited: set[Any] = set()

    def visit(node: Report) -> None:
        if node.pk in visited:  # defensive: a cycle in corrupt data must not loop
            return
        visited.add(node.pk)
        ordered.append(node)
        for child in sorted(children.get(node.pk, []), key=_fiction_sort_key):
            visit(child)

    for root in roots:
        visit(root)
    return ordered


def fiction_continuations(report: Report) -> list[Report]:
    """Direct continuations of ``report`` (its ``next_reports``), mainline-first.

    Same sort as :func:`fiction_thread` sibling ordering (branch_order, session_date,
    created_at): the mainline comes first, branches after. Feeds the closing
    « Next → » partial; the template stores no id.
    """
    return sorted(report.next_reports.all(), key=_fiction_sort_key)


@transaction.atomic
def set_previous(report: Report, new_previous: Report | None) -> None:
    """Set ``report.previous_report`` to ``new_previous`` after validating invariants.

    Rewrites exactly one edge. Branching is allowed, so no sibling is reparented and
    ``branch_order`` is untouched (explicit branch ordering is a separate gesture).
    Validation runs BEFORE writing: on failure nothing is persisted. Setting a local
    predecessor clears any ``previous_report_iri`` — the FK IS the link (XOR).
    """
    report.previous_report = new_previous
    if new_previous is not None:
        report.previous_report_iri = None
    validate_fiction_links(report)
    report.save(update_fields=["previous_report", "previous_report_iri", "updated_at"])
