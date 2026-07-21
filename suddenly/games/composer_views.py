"""
Post composer (Rapport) — the "création de post" screen (level Rapport) (DA-1).

Distinct from report_compose (which writes a whole Report/scene): this writes
a single Rapport into a scene, or opens a new scene around a PC. The context
(pc, game, role) is frozen server side — the client never chooses the target
Report, the author, or the role. See games/services.py for the gestures.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from ._view_helpers import _POST_MODES, _resolve_actor
from .models import Game, RapportStatus, Report
from .services import (
    build_composer_context,
    build_composer_feed_context,
    build_game_queryset,
    create_npc_in_cast,
    is_game_master,
    open_new_scene,
)


@login_required
def composer(request: AuthenticatedRequest) -> HttpResponse:
    """The unified post composer, opened from the feed (no frozen scene).

    Two selectors: PERSONNAGE then PARTIE. Picking a personnage recomputes the
    game list (origin game + games it is already cast into) — an HTMX GET with
    ``?region=game_field`` returns just that select. Picking a game recomputes
    role, cast and available kinds (rule 2c) — ``?region=context`` returns that
    region.

    POST opens the scene via :func:`open_new_scene`; it is refused (422, explicit
    message) when either personnage or partie is missing — brouillon compris
    (rule 2a).
    """
    from django.core.exceptions import ValidationError

    from suddenly.characters.models import Character

    src = request.POST if request.method == "POST" else request.GET

    game = None
    game_pk = src.get("game", "").strip()
    if game_pk:
        game = get_object_or_404(Game, pk=game_pk)

    character = None
    character_slug = src.get("character", "").strip()
    if character_slug:
        character = get_object_or_404(Character, slug=character_slug)

    if request.method == "POST":
        if game is None or character is None:
            return HttpResponse(
                "Choisissez un personnage et une partie avant d'envoyer (brouillon compris).",
                status=422,
            )
        mode = request.POST.get("mode", "add")
        if mode not in _POST_MODES:
            mode = "add"
        status = RapportStatus.DRAFT if mode == "draft" else RapportStatus.PUBLISHED
        actor = _resolve_actor(request)
        try:
            report, _rapport = open_new_scene(
                user=request.user,
                game=game,
                character=character,
                kind=request.POST.get("kind", ""),
                content=request.POST.get("content", "").strip(),
                actor=actor,
                status=status,
                image=request.FILES.get("image"),
                media_alt=request.POST.get("media_alt", "").strip(),
                content_warning=request.POST.get("content_warning", "").strip(),
            )
        except ValidationError as exc:
            return HttpResponse("; ".join(exc.messages), status=422)
        return redirect(
            reverse("games:report_edit", kwargs={"game_pk": report.game.pk, "pk": report.pk})
        )

    if getattr(request, "htmx", False) and request.GET.get("region") == "game_field":
        resp = render(
            request,
            "games/_composer_game_field.html",
            {
                "games": build_game_queryset(request.user, character=character),
                "reset_game": True,
            },
        )
        # Personnage change resets the game → clear the stale last-scene preview
        # out-of-band, parity with the region=context refresh below.
        resp.write('<div id="composer-last-scene" hx-swap-oob="true"></div>')
        return resp

    ctx = build_composer_feed_context(request.user, game=game, character=character)

    if getattr(request, "htmx", False) and request.GET.get("region") == "context":
        return render(request, "games/_composer_context_swap.html", ctx)

    return htmx_render(
        request,
        full_template="games/composer.html",
        partial_template="games/_composer.html",
        context=ctx,
    )


@require_POST
@login_required
def cast_npc_create(request: AuthenticatedRequest, game_pk: str) -> HttpResponse:
    """ "+ Nouveau PNJ": create the Character **and** its GameCast entry (GM only).

    Returns the recomputed composer context region, with the fresh NPC now in the
    actor pool and pre-selected (rule 2d).
    """
    game = get_object_or_404(Game, pk=game_pk)
    if not is_game_master(request.user, game):
        return HttpResponseForbidden()

    name = request.POST.get("name", "").strip()
    if not name:
        return HttpResponse("Un nom de PNJ est requis.", status=400)

    npc = create_npc_in_cast(
        user=request.user,
        game=game,
        name=name,
        description=request.POST.get("description", "").strip(),
    )

    report = None
    report_pk = request.POST.get("report", "").strip()
    if report_pk:
        report = get_object_or_404(
            Report.objects.select_related("game"),
            pk=report_pk,
            game=game,
            author=request.user,
        )

    ctx = build_composer_context(
        request.user,
        report=report,
        game=game,
        selected_actor=npc.slug,
        selected_actor_label=npc.name,
    )
    return render(request, "games/_composer_context.html", ctx)
