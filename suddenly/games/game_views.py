"""
Game CRUD, listing and public Stories views (DA-1).
"""

from __future__ import annotations

import datetime

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from ._view_helpers import _game_form_extra, _released_reports, _render_game_form
from .models import Game, Report, ReportStatus
from .services import build_game_queryset, known_game_systems, near_duplicate_system


def game_list(request: HttpRequest) -> HttpResponse:
    """Game list with filters (US-02)."""
    qs = build_game_queryset(
        user=request.user,
        q=request.GET.get("q", ""),
        system=request.GET.get("system", ""),
        tag=request.GET.get("tag", ""),
    )

    all_tags: list[str] = sorted(
        Game.objects.filter(remote=False, tags__isnull=False)
        .values_list("tags__name", flat=True)
        .distinct()
    )

    return htmx_render(
        request,
        full_template="games/list.html",
        partial_template="games/_list_results.html",
        context={
            "games": qs[:24],
            "system_filter": request.GET.get("system", ""),
            "active_tag": request.GET.get("tag", ""),
            "all_tags": all_tags,
        },
    )


def game_search(request: HttpRequest) -> HttpResponse:
    """HTMX endpoint for live game search (partial only)."""
    qs = build_game_queryset(
        user=request.user,
        q=request.GET.get("q", ""),
        system=request.GET.get("system", ""),
        tag=request.GET.get("tag", ""),
    )
    return htmx_render(
        request,
        full_template="games/_list_results.html",
        partial_template="games/_list_results.html",
        context={
            "games": qs[:24],
            "system_filter": request.GET.get("system", ""),
            "active_tag": request.GET.get("tag", ""),
        },
    )


def game_detail(request: HttpRequest, pk: str) -> HttpResponse:
    """Game profile / landing page — cast, meta, preview of reports (US-02).

    Role split with ``story_detail`` (SUD-V5), so the two public doors to a game
    are not redundant:

    - ``game_detail`` (this view) is the *profile*: game metadata, cast, follow
      button, and a bounded preview of the game's published reports. It answers
      "what is this game and who plays in it?". It is the owner-facing and
      discovery landing surface.
    - ``story_detail`` is the *long read*: the end-to-end aggregation of only the
      released reports (rapports + markers), the resolved account. It answers
      "let me read this story from start to finish".
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q

    from suddenly.characters.models import Follow

    visibility = Q(is_public=True)
    if request.user.is_authenticated:
        visibility |= Q(owner=request.user)

    game = get_object_or_404(Game.objects.select_related("owner").filter(visibility), pk=pk)

    # Owner-facing vs discovery: the owner sees their own reports still behind
    # the wall (published, not yet released) on their game page; any other visitor
    # only sees wall-cleared content (feed_visible), like the public feeds.
    if request.user.is_authenticated and request.user == game.owner:
        reports = game.reports.filter(status=ReportStatus.PUBLISHED).select_related("author")[:20]
    else:
        reports = game.reports.feed_visible().select_related("author")[:20]
    # Roster = characters *homed* in this game (origin_game). Exclude forks:
    # a fork inherits its parent's origin_game (its AP home) but originated
    # elsewhere, created by another player — it does not belong to this roster.
    characters = (
        game.characters.filter(parent__isnull=True)
        .select_related("creator", "owner")
        .order_by("-created_at")[:12]
    )

    is_following = False
    if request.user.is_authenticated and request.user != game.owner:
        ct = ContentType.objects.get_for_model(game)
        is_following = Follow.objects.filter(
            follower=request.user, content_type=ct, object_id=game.pk
        ).exists()

    # Direct-message entry point (Epic E, #135, DEC-E7) — read-only, gated by
    # mutuality; never writes a Follow. Targets the game's owner (the GM).
    dm_recipient = None
    if (
        request.user.is_authenticated
        and request.user != game.owner
        and Follow.objects.are_mutual(request.user, game.owner)
    ):
        dm_recipient = game.owner

    return htmx_render(
        request,
        full_template="games/detail.html",
        partial_template="games/detail.html",
        context={
            "game": game,
            "reports": reports,
            "characters": characters,
            "is_owner": request.user == game.owner if request.user.is_authenticated else False,
            "is_following": is_following,
            "dm_recipient": dm_recipient,
        },
    )


# ---------------------------------------------------------------------------
# Stories — public reading surface for released content (SUD-V3).
#
# Stories is the *compte rendu* side of the wall: it only ever shows reports
# that have crossed the temporal wall (released + published + public). The
# liberation filter lives in the queryset — an unreleased report never enters
# the context of these public views (structural wall, not a render-time mask).
# ---------------------------------------------------------------------------


def stories_index(request: HttpRequest) -> HttpResponse:
    """Public list of games that have at least one released story (SUD-V3).

    No @login_required: Stories is readable by everyone. Only games with
    released + published + public content are listed — the wall filter is in
    the queryset, so private/in-progress reports never surface here.
    """
    # Games with at least one released report — the wall filter stays centralized
    # in Report.objects.released() (SUD-V1); this view never re-expresses it.
    games = (
        Game.objects.filter(reports__in=Report.objects.released(), remote=False)
        .distinct()
        .select_related("owner")
        .order_by("-updated_at")
    )

    return htmx_render(
        request,
        full_template="stories/index.html",
        partial_template="stories/_index_results.html",
        context={"games": games[:30]},
    )


def story_detail(request: HttpRequest, pk: str) -> HttpResponse:
    """Public end-to-end reading of a game's released reports (SUD-V3).

    Aggregates *only* released reports (rapports + markers). A game with no
    released content is not a public story → 404. Unreleased reports are
    structurally absent from the context (filtered at the queryset).
    """
    game = get_object_or_404(Game.objects.select_related("owner").filter(remote=False), pk=pk)

    reports = list(_released_reports(game))
    if not reports:
        raise Http404

    from suddenly.characters.models import Quote

    quotes = Quote.objects.promotable().filter(report__game=game).order_by("-created_at")

    return htmx_render(
        request,
        full_template="stories/detail.html",
        partial_template="stories/detail.html",
        context={"game": game, "reports": reports, "quotes": quotes},
    )


@login_required
def game_create(request: AuthenticatedRequest) -> HttpResponse:
    """Create a new game (US-02)."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        is_public = request.POST.get("is_public") == "on"

        game_system_text = request.POST.get("game_system", "").strip()

        if not title:
            return _render_game_form(
                request,
                game=None,
                is_public_checked=is_public,
                form_data=request.POST,
                error=_("Title is required."),
            )

        # Near-duplicate game_system guard — force a confirmation when the entered
        # label is very close to an existing one but not identical (mirrors the
        # client-side check; the server is the enforcement).
        known = known_game_systems()
        if request.POST.get("system_confirmed") != "1":
            system_warning = near_duplicate_system(game_system_text, known)
            if system_warning:
                return _render_game_form(
                    request,
                    game=None,
                    is_public_checked=is_public,
                    form_data=request.POST,
                    system_warning=system_warning,
                    extra=_game_form_extra(known),
                )

        started_at_raw = request.POST.get("started_at", "").strip()
        try:
            started_at = datetime.date.fromisoformat(started_at_raw) if started_at_raw else None
        except ValueError:
            started_at = None

        cover = request.FILES.get("cover")
        game = Game.objects.create(
            title=title,
            description=description,
            game_system=game_system_text,
            is_public=is_public,
            owner=request.user,
            cover=cover,
            started_at=started_at,
        )
        from suddenly.core.models import Tag

        game.tags.set(Tag.resolve_names(request.POST.get("tags", "")))
        return redirect(reverse("games:detail", kwargs={"pk": game.pk}))

    return _render_game_form(request, game=None, is_public_checked=True, form_data={})


@login_required
def game_edit(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Edit a game (owner only)."""
    game = get_object_or_404(Game, pk=pk, owner=request.user)

    is_public_checked = (
        request.POST.get("is_public") == "on" if request.method == "POST" else game.is_public
    )

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            return _render_game_form(
                request,
                game=game,
                is_public_checked=is_public_checked,
                form_data=request.POST,
                error=_("Title is required."),
            )

        game_system_text = request.POST.get("game_system", "").strip()
        known = known_game_systems()
        if request.POST.get("system_confirmed") != "1":
            system_warning = near_duplicate_system(game_system_text, known)
            if system_warning:
                return _render_game_form(
                    request,
                    game=game,
                    is_public_checked=is_public_checked,
                    form_data=request.POST,
                    system_warning=system_warning,
                    extra=_game_form_extra(known),
                )

        game.title = title
        game.description = request.POST.get("description", "").strip()
        game.game_system = game_system_text
        game.is_public = is_public_checked

        started_at_raw = request.POST.get("started_at", "").strip()
        try:
            game.started_at = (
                datetime.date.fromisoformat(started_at_raw) if started_at_raw else None
            )
        except ValueError:
            game.started_at = None

        if request.POST.get("cover-clear"):
            if game.cover:
                game.cover.delete(save=False)
            game.cover = None
        elif "cover" in request.FILES:
            game.cover = request.FILES["cover"]

        game.save(
            update_fields=[
                "title",
                "description",
                "game_system",
                "is_public",
                "started_at",
                "cover",
                "updated_at",
            ]
        )

        from suddenly.core.models import Tag

        game.tags.set(Tag.resolve_names(request.POST.get("tags", "")))

        return redirect(reverse("games:detail", kwargs={"pk": game.pk}))

    return _render_game_form(request, game=game, is_public_checked=game.is_public, form_data={})


@login_required
def game_delete(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Delete a game (owner only, no PCs inside)."""
    game = get_object_or_404(Game, pk=pk, owner=request.user)
    if request.method == "POST":
        pc_statuses = ["pc", "claimed", "adopted"]
        if game.characters.filter(status__in=pc_statuses).exists():
            return redirect(reverse("games:detail", kwargs={"pk": game.pk}))
        game.delete()
    return redirect(reverse("games:list"))


@login_required
def game_delete_bulk(request: AuthenticatedRequest) -> HttpResponse:
    """Bulk delete games (owner only, no PCs inside)."""
    if request.method == "POST":
        pc_statuses = ["pc", "claimed", "adopted"]
        pks = request.POST.getlist("pks")
        for game in Game.objects.filter(pk__in=pks, owner=request.user):
            if not game.characters.filter(status__in=pc_statuses).exists():
                game.delete()
    return redirect(reverse("games:list"))
