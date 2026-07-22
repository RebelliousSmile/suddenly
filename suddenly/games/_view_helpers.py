"""
Shared helpers for the games front views (DA-1).

Underscore-prefixed scaffolding relocated verbatim from the former
``front_views.py`` monolith. View modules import from here; this module never
imports a view module (no circular imports).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from .models import (
    CHARACTER_MARKER_KINDS,
    Game,
    MarkerKind,
    Rapport,
    RapportMarker,
    RapportStatus,
    Report,
)
from .services import known_game_systems

if TYPE_CHECKING:
    from suddenly.characters.models import Character
    from suddenly.users.models import User

# Split-button send modes of the composer.
_POST_MODES = frozenset({"add", "add_continue", "draft"})


def _game_form_extra(known: list[str] | None = None) -> dict[str, object]:
    """Shared game-form context: known systems (most-used first), consumed
    client-side by the gameForm Alpine component for the suggestion dropdown."""
    known = known_game_systems() if known is None else known
    return {"system_known": known}


def _forbid_non_author(
    report: Report | None, request: AuthenticatedRequest
) -> HttpResponseForbidden | None:
    """Single source of the scene-author gate.

    Returns a bare ``HttpResponseForbidden`` (empty body, as the inline checks
    did) when ``report`` is missing or the caller is not its author, else
    ``None``. A ``None`` report yields 403.
    """
    if report is None or report.author != request.user:
        return HttpResponseForbidden()
    return None


def _render_game_form(
    request: AuthenticatedRequest,
    *,
    game: Game | None,
    is_public_checked: bool,
    form_data: object,
    error: object = None,
    system_warning: object = None,
    extra: dict[str, object] | None = None,
) -> HttpResponse:
    """Single re-render of ``games/game_form.html`` for create + edit.

    ``error`` and ``system_warning`` are added to the context only when given,
    reproducing each prior per-branch context byte-for-byte. ``extra`` overrides
    the default ``_game_form_extra()`` (used for the near-duplicate system path
    that passes the already-computed known list).
    """
    context: dict[str, object] = {
        "game": game,
        "is_public_checked": is_public_checked,
        "form_data": form_data,
        **(_game_form_extra() if extra is None else extra),
    }
    if error is not None:
        context["error"] = error
    if system_warning is not None:
        context["system_warning"] = system_warning
    return htmx_render(
        request,
        full_template="games/game_form.html",
        partial_template="games/game_form.html",
        context=context,
    )


def _released_reports(game: Game) -> models.QuerySet[Report]:
    """Reports of a game that have crossed the wall, in reading order."""
    return (
        game.reports.released()
        .select_related("author")
        .prefetch_related(
            # Public reading surface: only published rapports cross into a story.
            models.Prefetch(
                "rapports",
                queryset=Rapport.objects.filter(status=RapportStatus.PUBLISHED).select_related(
                    "actor"
                ),
            ),
            "rapports__markers__character",
            "rapports__parent_links__parent_rapport",
        )
        .order_by(
            models.F("session_date").asc(nulls_last=True),
            "released_at",
            "created_at",
        )
    )


def _user_has_character_in_game(user: User, game: Game) -> bool:
    """Return True if the user has at least one character originating from this game."""
    from suddenly.characters.models import Character

    return Character.objects.filter(creator=user, origin_game=game).exists()


def _resolve_actor(request: AuthenticatedRequest) -> Character | None:
    """Resolve the submitted ``actor`` (character slug) or ``None``.

    Returns the Character or None; ownership/role is revalidated by the service
    layer, not here (a slug that resolves to a character outside the vivier is
    rejected at creation time).
    """
    from suddenly.characters.models import Character

    slug = request.POST.get("actor", "").strip()
    if not slug:
        return None
    return get_object_or_404(Character, slug=slug)


def _get_scene_rapport(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> Rapport:
    """Fetch a rapport within the given scene/game, or raise 404.

    Does **not** check authorship — callers gate with ``_forbid_non_author``.
    """
    return get_object_or_404(
        Rapport.objects.select_related("report__game", "report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )


def _scene_rapports(report: Report) -> models.QuerySet[Rapport]:
    """The scene's Rapports, prefetched for the fil, in sequence order."""
    return report.rapports.select_related("actor").prefetch_related(
        "parent_links__parent_rapport", "markers__character", "media"
    )


def _scene_departures(report: Report) -> set[str]:
    """Character ids currently 'gone' from the scene.

    A character has left when their last entrance/exit marker in narrative
    order (rapport sequence, then creation) is CHARACTER_LEAVES; a later
    CHARACTER_APPEARS brings them back. Values-only read — no model overhead.
    """
    last_kind: dict[str, str] = {}
    markers = (
        RapportMarker.objects.filter(
            rapport__report=report,
            kind__in=CHARACTER_MARKER_KINDS,
            character__isnull=False,
        )
        .order_by("rapport__order", "rapport__created_at", "created_at")
        .values_list("character_id", "kind")
    )
    for character_id, kind in markers:
        last_kind[str(character_id)] = kind
    return {cid for cid, kind in last_kind.items() if kind == MarkerKind.CHARACTER_LEAVES}


def _scene_cast(report: Report) -> list[Character]:
    """The scene's cast for the collapsible box (_cast_box.html): characters
    brought in by ReportCast plus anyone who has spoken/acted, each flagged with
    the transient view-model attribute ``has_left`` from entrance/exit markers.

    Shared by the reader (report_detail) and the editor (report_edit).
    """
    from suddenly.characters.models import Character

    cast_ids = set(report.cast.filter(character__isnull=False).values_list("character", flat=True))
    cast_ids |= set(report.rapports.filter(actor__isnull=False).values_list("actor", flat=True))
    gone_ids = _scene_departures(report)
    scene_cast = list(
        Character.objects.filter(pk__in=cast_ids).select_related("origin_game").order_by("name")
    )
    for character in scene_cast:
        # Transient view-model attribute the model does not declare; the mypy
        # attr-defined check is silenced here.
        character.has_left = str(character.pk) in gone_ids  # type: ignore[attr-defined]
    return scene_cast
