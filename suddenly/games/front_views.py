"""
HTMX-first views for games and reports (DA-1).
"""

from __future__ import annotations

import datetime
from collections import OrderedDict
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from suddenly.core.models import InstanceSettings
from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

if TYPE_CHECKING:
    from suddenly.characters.models import Character
    from suddenly.users.models import User

from .marker_forms import RapportMarkerForm
from .models import (
    CastRole,
    Game,
    Rapport,
    RapportLink,
    RapportMarker,
    RapportMedia,
    RapportStatus,
    Report,
    ReportCast,
    ReportStatus,
    ReportVisibility,
)
from .rapport_forms import RapportForm
from .services import (
    available_kinds,
    build_actor_pool,
    build_game_cast,
    build_game_queryset,
    close_scene,
    create_npc_in_cast,
    create_scene_post,
    is_game_master,
    open_new_scene,
    publish_report,
    reopen_scene,
)


@login_required
def report_compose(request: AuthenticatedRequest) -> HttpResponse:
    """Quick compose page for a new report, linked to a character's game."""
    from django.conf import settings as django_settings

    from suddenly.characters.models import Character

    characters = (
        Character.objects.filter(
            origin_game__owner=request.user,
            origin_game__remote=False,
        )
        .select_related("origin_game")
        .order_by("name")
    )

    default_language = InstanceSettings.get().language
    selected_slug = request.GET.get("character", "")

    if request.method == "POST":
        character_slug = request.POST.get("character_slug", "").strip()
        content = request.POST.get("content", "").strip()
        language = request.POST.get("language", default_language)
        cw = request.POST.get("content_warning", "").strip()
        visibility = request.POST.get("visibility", ReportVisibility.PUBLIC)
        action = request.POST.get("action", "draft")

        character = get_object_or_404(
            Character,
            slug=character_slug,
            origin_game__owner=request.user,
            origin_game__remote=False,
        )

        if not content:
            return htmx_render(
                request,
                full_template="games/report_compose.html",
                partial_template="games/report_compose.html",
                context={
                    "characters": characters,
                    "selected_slug": character_slug,
                    "default_language": language,
                    "visibilities": ReportVisibility.choices,
                    "languages": django_settings.LANGUAGES,
                    "error": _("Content is required."),
                    "form_data": request.POST,
                },
            )

        report = Report.objects.create(
            content=content,
            content_warning=cw,
            visibility=visibility,
            language=language,
            game=character.origin_game,
            author=request.user,
            status=ReportStatus.DRAFT,
        )

        ReportCast.objects.create(
            report=report,
            character=character,
            role=CastRole.MAIN,
        )

        if action == "publish":
            publish_report(report, request.user)

        return redirect(
            reverse(
                "games:report_detail",
                kwargs={"game_pk": character.origin_game.pk, "pk": report.pk},
            )
        )

    return htmx_render(
        request,
        full_template="games/report_compose.html",
        partial_template="games/report_compose.html",
        context={
            "characters": characters,
            "selected_slug": selected_slug,
            "default_language": default_language,
            "visibilities": ReportVisibility.choices,
            "languages": django_settings.LANGUAGES,
            "form_data": {},
        },
    )


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

    reports = game.reports.filter(status=ReportStatus.PUBLISHED).select_related("author")[:20]
    characters = game.characters.select_related("creator", "owner").order_by("-created_at")[:12]

    is_following = False
    if request.user.is_authenticated and request.user != game.owner:
        ct = ContentType.objects.get_for_model(game)
        is_following = Follow.objects.filter(
            follower=request.user, content_type=ct, object_id=game.pk
        ).exists()

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


@require_POST
@login_required
def report_release(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Cross (or re-close) the temporal wall for one of the author's reports (SUD-V4).

    Deliberate act that turns a game in progress into a resolved account.
    Reversible while the report has not been federated (no ap_id); once
    federated, release is irreversible — the wall protected discovery, it was
    never a perpetual secret.
    """
    report = get_object_or_404(Report, pk=pk, game_id=game_pk, author=request.user)

    # Only a published report can cross the wall — releasing a draft would put
    # nothing in Stories (which also requires PUBLISHED).
    if report.status != ReportStatus.PUBLISHED:
        return HttpResponse(_("Only a published report can be released."), status=400)

    if report.released_at is None:
        report.released_at = timezone.now()
        report.save(update_fields=["released_at", "updated_at"])
    elif not report.ap_id:
        # Not yet federated → re-closing the wall is allowed.
        report.released_at = None
        report.save(update_fields=["released_at", "updated_at"])
    # else: federated + already released → irreversible, leave untouched.

    return redirect(
        reverse("games:report_detail", kwargs={"game_pk": report.game_id, "pk": report.pk})
    )


@require_POST
@login_required
def scene_close(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Close a scene from the scene-edit dock (draft → closed, or → released).

    Optionally writes the closure Rapport (the compte rendu) from ``closure``.
    ``mode=release`` closes *and* crosses the wall; anything else just closes.
    """
    report = get_object_or_404(Report, pk=pk, game_id=game_pk, author=request.user)
    close_scene(
        report=report,
        user=request.user,
        closure_content=request.POST.get("closure", ""),
        release=request.POST.get("mode") == "release",
    )
    return redirect(
        reverse("games:report_edit", kwargs={"game_pk": report.game_id, "pk": report.pk})
    )


@require_POST
@login_required
def scene_reopen(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Reopen a closed scene back to draft (scene-edit dock)."""
    from django.core.exceptions import ValidationError

    report = get_object_or_404(Report, pk=pk, game_id=game_pk, author=request.user)
    try:
        reopen_scene(report=report)
    except ValidationError as exc:
        return HttpResponse("; ".join(exc.messages), status=400)
    return redirect(
        reverse("games:report_edit", kwargs={"game_pk": report.game_id, "pk": report.pk})
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
            return htmx_render(
                request,
                full_template="games/game_form.html",
                partial_template="games/game_form.html",
                context={
                    "game": None,
                    "error": _("Title is required."),
                    "form_data": request.POST,
                    "is_public_checked": request.POST.get("is_public") == "on",
                },
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
        return redirect(reverse("games:detail", kwargs={"pk": game.pk}))

    return htmx_render(
        request,
        full_template="games/game_form.html",
        partial_template="games/game_form.html",
        context={"game": None, "is_public_checked": True, "form_data": {}},
    )


def report_detail(request: HttpRequest, game_pk: str, pk: str) -> HttpResponse:
    """Report detail page (US-04)."""
    report = get_object_or_404(
        Report.objects.select_related("game", "author").prefetch_related(
            "rapports__parent_links",
            "rapports__parent_links__parent_rapport",
        ),
        pk=pk,
        game_id=game_pk,
    )

    # Wall check (SUD-V2): a report must be BOTH published (federation axis)
    # AND released (liberation axis) to be visible to the public. A report that
    # is published but not yet released is still a game in progress behind the
    # wall — only its author may read it.
    if report.status != ReportStatus.PUBLISHED or not report.is_released:
        if not request.user.is_authenticated or request.user != report.author:
            raise Http404

    from suddenly.characters.models import Character, Quote

    cast = report.character_appearances.select_related("character").order_by("role")
    # Fallback for ingested reports: CharacterAppearance not created via ingest endpoint,
    # so fall back to ReportCast (new_character_name entries) when appearances are absent.
    cast_fallback = report.cast.all() if not cast.exists() else None

    # Public "Citations retenues": the double lock, never re-expressed here.
    quotes = Quote.objects.promotable().filter(report=report).order_by("-created_at")[:5]

    # Draft rapports are private to their author: the author manages them here
    # (edit/publish), but the public thread of a released report shows only
    # published rapports (per-rapport wall, decision #1 option A).
    is_author = request.user.is_authenticated and request.user == report.author

    # §5: the author marks a réplique as citation. They manage every quote of
    # this report (regardless of the wall), and pick a speaker among its cast.
    manage_quotes = None
    quote_characters = None
    if is_author:
        manage_quotes = report.quotes.select_related("character").order_by("-created_at")
        quote_characters = Character.objects.filter(
            models.Q(appearances__report=report) | models.Q(cast_entries__report=report)
        ).distinct()

    rapports = report.rapports.select_related("actor").prefetch_related(
        "parent_links__parent_rapport", "markers__character"
    )
    if not is_author:
        rapports = rapports.filter(status=RapportStatus.PUBLISHED)

    return htmx_render(
        request,
        full_template="games/report_detail.html",
        partial_template="games/report_detail.html",
        context={
            "report": report,
            "game": report.game,
            "cast": cast,
            "cast_fallback": cast_fallback,
            "quotes": quotes,
            "is_author": is_author,
            "manage_quotes": manage_quotes,
            "quote_characters": quote_characters,
            "rapports": rapports,
        },
    )


@login_required
def report_thread(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Thread reading view for a Report — Flux (paginated) or Grouped by parent (US-31)."""
    report = get_object_or_404(
        Report.objects.select_related("game", "author"),
        pk=pk,
        game_id=game_pk,
    )

    # Same visibility check as report_detail
    if report.status != ReportStatus.PUBLISHED:
        if not request.user.is_authenticated or request.user != report.author:
            raise Http404

    game = report.game
    _mode_param = request.GET.get("mode")
    mode: str = _mode_param if _mode_param in ("flux", "group") else "flux"

    # The fil renders only published rapports; the author keeps seeing their own
    # drafts (they manage/publish them from here).
    is_author = request.user.is_authenticated and request.user == report.author
    rapport_base = (
        report.rapports if is_author else report.rapports.filter(status=RapportStatus.PUBLISHED)
    )

    if getattr(request, "htmx", False):
        if mode == "group":
            rapports_qs = (
                rapport_base.select_related("actor")
                .prefetch_related("parent_links__parent_rapport")
                .order_by("created_at")
            )
            groups: OrderedDict[object, list[Rapport]] = OrderedDict()
            for rapport in rapports_qs:
                all_links = rapport.parent_links.all()
                first_link = all_links[0] if all_links.exists() else None
                key = (
                    first_link.parent_rapport_id
                    if first_link and first_link.parent_rapport_id
                    else None
                )
                groups.setdefault(key, []).append(rapport)
            return render(
                request,
                "games/partials/thread_group_view.html",
                {
                    "report": report,
                    "game": game,
                    "mode": mode,
                    "scenes": list(groups.items()),
                },
            )
        else:
            # mode == "flux"
            rapports_qs = rapport_base.select_related("actor").order_by("created_at")
            page_number = request.GET.get("page", 1)
            paginator = Paginator(rapports_qs, 10)
            page_obj = paginator.get_page(page_number)
            return render(
                request,
                "games/partials/thread_flux_page.html",
                {
                    "report": report,
                    "game": game,
                    "mode": mode,
                    "page_obj": page_obj,
                    "has_next": page_obj.has_next(),
                    "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
                },
            )

    # Full page render (non-HTMX)
    if mode == "group":
        rapports_qs = (
            rapport_base.select_related("actor")
            .prefetch_related("parent_links__parent_rapport")
            .order_by("created_at")
        )
        groups = OrderedDict()
        for rapport in rapports_qs:
            all_links = rapport.parent_links.all()
            first_link = all_links[0] if all_links.exists() else None
            key = (
                first_link.parent_rapport_id
                if first_link and first_link.parent_rapport_id
                else None
            )
            groups.setdefault(key, []).append(rapport)
        return render(
            request,
            "games/thread.html",
            {
                "report": report,
                "game": game,
                "mode": mode,
                "scenes": list(groups.items()),
                "page_obj": None,
                "has_next": False,
                "next_page": None,
            },
        )
    else:
        # mode == "flux"
        rapports_qs = rapport_base.select_related("actor").order_by("created_at")
        page_number = request.GET.get("page", 1)
        paginator = Paginator(rapports_qs, 10)
        page_obj = paginator.get_page(page_number)
        return render(
            request,
            "games/thread.html",
            {
                "report": report,
                "game": game,
                "mode": mode,
                "page_obj": page_obj,
                "has_next": page_obj.has_next(),
                "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
                "scenes": [],
            },
        )


@login_required
def report_create(request: AuthenticatedRequest, game_pk: str) -> HttpResponse:
    """Create a new report (US-04, US-05)."""
    game = get_object_or_404(Game, pk=game_pk, owner=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        cw = request.POST.get("content_warning", "").strip()
        visibility = request.POST.get("visibility", ReportVisibility.PUBLIC)
        action = request.POST.get("action", "draft")

        if not content:
            return htmx_render(
                request,
                full_template="games/report_form.html",
                partial_template="games/report_form.html",
                context={
                    "game": game,
                    "report": None,
                    "error": _("Content is required."),
                    "form_data": request.POST,
                    "visibilities": ReportVisibility.choices,
                },
            )

        session_date_raw = request.POST.get("session_date", "").strip()
        try:
            session_date = (
                datetime.date.fromisoformat(session_date_raw) if session_date_raw else None
            )
        except ValueError:
            session_date = None

        report = Report.objects.create(
            title=title,
            content=content,
            content_warning=cw,
            visibility=visibility,
            game=game,
            author=request.user,
            status=ReportStatus.DRAFT,
            session_date=session_date,
        )

        if action == "publish":
            publish_report(report, request.user)

        return redirect(
            reverse(
                "games:report_edit",
                kwargs={"game_pk": game.pk, "pk": report.pk},
            )
        )

    return htmx_render(
        request,
        full_template="games/report_form.html",
        partial_template="games/report_form.html",
        context={
            "game": game,
            "report": None,
            "visibilities": ReportVisibility.choices,
            "form_data": {},
        },
    )


@login_required
def report_edit(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Edit an existing report (author only)."""
    report = get_object_or_404(
        Report.objects.select_related("game").prefetch_related("cast__character"),
        pk=pk,
        game_id=game_pk,
        author=request.user,
    )

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        action = request.POST.get("action", "draft")

        if not content:
            return htmx_render(
                request,
                full_template="games/report_form.html",
                partial_template="games/report_form.html",
                context={
                    "report": report,
                    "game": report.game,
                    "error": _("Content is required."),
                    "form_data": request.POST,
                    "visibilities": ReportVisibility.choices,
                },
            )

        report.title = request.POST.get("title", "").strip()
        report.content = content
        report.content_warning = request.POST.get("content_warning", "").strip()
        report.visibility = request.POST.get("visibility", ReportVisibility.PUBLIC)

        session_date_raw = request.POST.get("session_date", "").strip()
        try:
            report.session_date = (
                datetime.date.fromisoformat(session_date_raw) if session_date_raw else None
            )
        except ValueError:
            report.session_date = None

        report.save(
            update_fields=[
                "title",
                "content",
                "content_warning",
                "visibility",
                "session_date",
                "updated_at",
            ]
        )

        if action == "publish" and report.status != ReportStatus.PUBLISHED:
            publish_report(report, request.user)

        return redirect(
            reverse("games:report_detail", kwargs={"game_pk": report.game.pk, "pk": report.pk})
        )

    # The fil of the scene, shown beside the composer (Mastodon-style). The
    # author sees drafts too; they are hidden from the public thread elsewhere.
    rapports = (
        report.rapports.select_related("actor")
        .prefetch_related("parent_links__parent_rapport", "markers__character", "media")
        .order_by("created_at")
    )

    return htmx_render(
        request,
        full_template="games/report_form.html",
        partial_template="games/report_form.html",
        context={
            "report": report,
            "game": report.game,
            "visibilities": ReportVisibility.choices,
            "cast_roles": CastRole.choices,
            "form_data": {},
            "rapports": rapports,
            # The unified post composer (same _composer.html as the feed), frozen
            # to this scene: game/personnage/language inherited, not editable.
            **_composer_context(request.user, report=report),
        },
    )


@require_POST
@login_required
def cast_add(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Add a character to the report cast (HTMX, US-13)."""
    from suddenly.characters.models import Character

    report = get_object_or_404(Report, pk=pk, game_id=game_pk, author=request.user)

    if report.status == ReportStatus.PUBLISHED:
        return HttpResponse("Cannot modify cast of a published report.", status=400)

    character = None
    character_slug = request.POST.get("character_slug", "").strip()
    if character_slug:
        character = get_object_or_404(Character, slug=character_slug, origin_game=report.game)
    new_name = request.POST.get("new_character_name", "").strip()
    new_desc = request.POST.get("new_character_description", "").strip()
    role = request.POST.get("role", CastRole.MENTIONED)

    if not character_slug and not new_name:
        return HttpResponse("At least one of character or new NPC name is required.", status=400)

    if role not in CastRole.values:
        role = CastRole.MENTIONED

    entry = ReportCast.objects.get_or_create(
        report=report,
        character=character,
        new_character_name=new_name if not character else "",
        defaults={"new_character_description": new_desc, "role": role},
    )[0]
    return render(
        request,
        "games/_cast_entry.html",
        {"entry": entry, "report": report, "game": report.game},
    )


@require_POST
@login_required
def cast_remove(request: AuthenticatedRequest, game_pk: str, pk: str, cast_pk: str) -> HttpResponse:
    """Remove a character from the report cast (HTMX, US-13)."""
    report = get_object_or_404(Report, pk=pk, game_id=game_pk, author=request.user)
    entry = get_object_or_404(ReportCast, pk=cast_pk, report=report)
    entry.delete()
    return HttpResponse("")


@login_required
def cast_mention_search(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Return cast members matching a query for @mention autocomplete (US-13)."""
    from django.http import JsonResponse

    report = get_object_or_404(Report, pk=pk, game_id=game_pk, author=request.user)
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    results: list[dict[str, str]] = []
    for entry in report.cast.select_related("character"):
        if entry.character:
            name: str = entry.character.name
            slug: str = entry.character.slug
        else:
            name = entry.new_character_name
            slug = ""
        if q.lower() in name.lower():
            results.append({"name": name, "slug": slug})
    return JsonResponse(results, safe=False)


@login_required
def cast_character_search(request: AuthenticatedRequest, game_pk: str) -> HttpResponse:
    """Search characters in a game for cast autocomplete (HTMX, US-13)."""
    from suddenly.characters.models import Character

    game = get_object_or_404(Game, pk=game_pk, owner=request.user)
    q = request.GET.get("q", "").strip()
    characters: list[object] = []
    if len(q) >= 2:
        characters = list(
            Character.objects.filter(origin_game=game, name__icontains=q).values("slug", "name")[
                :10
            ]
        )
    return render(
        request,
        "games/_cast_character_search_results.html",
        {"characters": characters},
    )


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
            return htmx_render(
                request,
                full_template="games/game_form.html",
                partial_template="games/game_form.html",
                context={
                    "game": game,
                    "error": _("Title is required."),
                    "form_data": request.POST,
                    "is_public_checked": is_public_checked,
                },
            )
        game.title = title
        game.description = request.POST.get("description", "").strip()
        game.game_system = request.POST.get("game_system", "").strip()
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

        tags_raw = request.POST.get("tags", "").strip()
        from suddenly.core.models import Tag

        tag_objects = [
            Tag.objects.get_or_create(name=name)[0]
            for name in [t.strip() for t in tags_raw.split(",") if t.strip()]
        ]
        game.tags.set(tag_objects)

        return redirect(reverse("games:detail", kwargs={"pk": game.pk}))

    return htmx_render(
        request,
        full_template="games/game_form.html",
        partial_template="games/game_form.html",
        context={"game": game, "is_public_checked": game.is_public, "form_data": {}},
    )


@login_required
def game_delete(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Delete a game (owner only, no PCs inside)."""
    game = get_object_or_404(Game, pk=pk, owner=request.user)
    if request.method == "POST":
        pc_statuses = ["pc", "claimed", "adopted", "forked"]
        if game.characters.filter(status__in=pc_statuses).exists():
            return redirect(reverse("games:detail", kwargs={"pk": game.pk}))
        game.delete()
    return redirect(reverse("games:list"))


@login_required
def game_delete_bulk(request: AuthenticatedRequest) -> HttpResponse:
    """Bulk delete games (owner only, no PCs inside)."""
    if request.method == "POST":
        pc_statuses = ["pc", "claimed", "adopted", "forked"]
        pks = request.POST.getlist("pks")
        for game in Game.objects.filter(pk__in=pks, owner=request.user):
            if not game.characters.filter(status__in=pc_statuses).exists():
                game.delete()
    return redirect(reverse("games:list"))


@login_required
def rapport_create(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    from django.shortcuts import render as _render
    from django.template.loader import render_to_string

    report = get_object_or_404(Report.objects.select_related("game"), pk=pk, game__pk=game_pk)
    if report.author != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = RapportForm(request.POST, game=report.game)
        form.full_clean()
        if form.is_valid():
            rapport = form.save(commit=False)
            rapport.report = report
            # In-scene add gesture: goes straight into the fil.
            rapport.status = RapportStatus.PUBLISHED
            rapport.save()
            html = render_to_string(
                "games/partials/rapport_item.html", {"rapport": rapport}, request=request
            )
            return HttpResponse(html)
        return _render(
            request,
            "games/rapport_form.html",
            {"form": form, "report": report},
            status=422,
        )
    form = RapportForm(game=report.game)
    return htmx_render(
        request,
        full_template="games/rapport_form.html",
        partial_template="games/rapport_form.html",
        context={"form": form, "report": report},
    )


@login_required
def rapport_edit(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    from django.shortcuts import render as _render
    from django.template.loader import render_to_string

    rapport = get_object_or_404(
        Rapport.objects.select_related("report__game", "report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )
    if rapport.report.author != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = RapportForm(request.POST, instance=rapport, game=rapport.report.game)
        form.full_clean()
        if form.is_valid():
            form.save()
            html = render_to_string(
                "games/partials/rapport_item.html", {"rapport": rapport}, request=request
            )
            return HttpResponse(html)
        return _render(
            request,
            "games/rapport_form.html",
            {"form": form, "report": rapport.report},
            status=422,
        )
    form = RapportForm(instance=rapport, game=rapport.report.game)
    return htmx_render(
        request,
        full_template="games/rapport_form.html",
        partial_template="games/rapport_form.html",
        context={"form": form, "report": rapport.report},
    )


@login_required
def rapport_delete(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    rapport = get_object_or_404(
        Rapport.objects.select_related("report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )
    if rapport.report.author != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        rapport.delete()
    return HttpResponse("")


@login_required
def marker_create(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    from django.shortcuts import render as _render
    from django.template.loader import render_to_string

    rapport = get_object_or_404(
        Rapport.objects.select_related("report__game", "report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )
    if rapport.report.author != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = RapportMarkerForm(request.POST, game=rapport.report.game)
        if form.is_valid():
            marker = form.save(commit=False)
            marker.rapport = rapport
            marker.save()
            rapport_refreshed = get_object_or_404(
                Rapport.objects.prefetch_related("markers", "markers__character"),
                pk=rapport_pk,
            )
            html = render_to_string(
                "games/partials/rapport_item.html",
                {"rapport": rapport_refreshed, "report": rapport_refreshed.report},
                request=request,
            )
            return HttpResponse(html)
        return _render(
            request,
            "games/marker_form.html",
            {"form": form, "rapport": rapport},
            status=422,
        )
    form = RapportMarkerForm(game=rapport.report.game)
    return htmx_render(
        request,
        full_template="games/marker_form.html",
        partial_template="games/marker_form.html",
        context={"form": form, "rapport": rapport},
    )


@login_required
def marker_delete(
    request: AuthenticatedRequest,
    game_pk: str,
    pk: str,
    rapport_pk: str,
    marker_pk: str,
) -> HttpResponse:
    marker = get_object_or_404(
        RapportMarker.objects.select_related("rapport__report__author"),
        pk=marker_pk,
        rapport__pk=rapport_pk,
        rapport__report__pk=pk,
        rapport__report__game__pk=game_pk,
    )
    if marker.rapport.report.author != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        marker.delete()
    return HttpResponse("")


def _user_has_character_in_game(user: User, game: Game) -> bool:
    """Return True if the user has at least one character originating from this game."""
    from suddenly.characters.models import Character

    return Character.objects.filter(creator=user, origin_game=game).exists()


@login_required
def rapport_reply(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    """Reply to a Rapport by creating a child Rapport with a local RapportLink parent."""
    from django.shortcuts import render as _render
    from django.template.loader import render_to_string

    rapport = get_object_or_404(
        Rapport.objects.select_related("report__game", "report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )
    game = rapport.report.game

    if not _user_has_character_in_game(request.user, game):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = RapportForm(request.POST, game=game)
        form.full_clean()
        if form.is_valid():
            child_rapport = form.save(commit=False)
            child_rapport.report = rapport.report
            # A reply is a public thread gesture: it appears in the fil.
            child_rapport.status = RapportStatus.PUBLISHED
            child_rapport.full_clean()
            child_rapport.save()

            link = RapportLink(rapport=child_rapport, parent_rapport=rapport)
            link.full_clean()
            link.save()

            child_rapport_refreshed = (
                Rapport.objects.prefetch_related(
                    "parent_links",
                    "parent_links__parent_rapport",
                    "markers",
                    "markers__character",
                )
                .select_related("report__game", "report__author", "actor")
                .get(pk=child_rapport.pk)
            )

            html = render_to_string(
                "games/partials/rapport_item.html",
                {"rapport": child_rapport_refreshed, "report": child_rapport_refreshed.report},
                request=request,
            )
            return HttpResponse(html)

        return _render(
            request,
            "games/partials/rapport_reply_form.html",
            {"form": form, "parent": rapport, "report": rapport.report, "game": game},
            status=422,
        )

    # GET
    form = RapportForm(game=game)
    return _render(
        request,
        "games/partials/rapport_reply_form.html",
        {"form": form, "parent": rapport, "report": rapport.report, "game": game},
    )


@login_required
def rapport_add_remote_parent(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    """Add a remote ActivityPub IRI as a parent of a Rapport (author only, POST-only)."""
    from django.core.validators import URLValidator
    from django.template.loader import render_to_string

    if request.method != "POST":
        from django.http import HttpResponseNotAllowed

        return HttpResponseNotAllowed(["POST"])

    rapport = get_object_or_404(
        Rapport.objects.select_related("report__game", "report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )

    if rapport.report.author != request.user:
        return HttpResponseForbidden()

    parent_iri = request.POST.get("parent_iri", "").strip()
    validate_url = URLValidator()

    try:
        validate_url(parent_iri)
    except Exception:
        rapport_refreshed = (
            Rapport.objects.prefetch_related(
                "parent_links",
                "parent_links__parent_rapport",
                "markers",
                "markers__character",
            )
            .select_related("report__game", "report__author", "actor")
            .get(pk=rapport.pk)
        )
        html = render_to_string(
            "games/partials/rapport_item.html",
            {
                "rapport": rapport_refreshed,
                "report": rapport_refreshed.report,
                "remote_parent_error": _("Please enter a valid URL."),
            },
            request=request,
        )
        return HttpResponse(html, status=422)

    link = RapportLink(rapport=rapport, parent_iri=parent_iri)
    link.full_clean()
    link.save()

    rapport_refreshed = (
        Rapport.objects.prefetch_related(
            "parent_links",
            "parent_links__parent_rapport",
            "markers",
            "markers__character",
        )
        .select_related("report__game", "report__author", "actor")
        .get(pk=rapport.pk)
    )
    html = render_to_string(
        "games/partials/rapport_item.html",
        {"rapport": rapport_refreshed, "report": rapport_refreshed.report},
        request=request,
    )
    return HttpResponse(html)


# ---------------------------------------------------------------------------
# Post composer (Rapport) — the "création de post" screen (level Rapport).
#
# Distinct from report_compose (which writes a whole Report/scene): this writes
# a single Rapport into a scene, or opens a new scene around a PC. The context
# (pc, game, role) is frozen server side — the client never chooses the target
# Report, the author, or the role. See games/services.py for the gestures.
# ---------------------------------------------------------------------------

# Split-button send modes of the composer.
_POST_MODES = frozenset({"add", "add_continue", "draft"})


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


@require_POST
@login_required
def scene_post_create(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Create one Rapport (post) inside an existing scene.

    Modes (menu of the split-button): ``add`` / ``add_continue`` publish into the
    fil, ``draft`` keeps a private draft (decision #1, option A). All three, on
    HTMX, post inline (Mastodon-style): the new Rapport is appended to the fil
    (OOB) and a fresh composer replaces the old one — no page reload. Non-HTMX
    callers fall back to a redirect to the scene edit.

    The target Report and its author come from the server: only the report's
    author may add to it, and the actor is revalidated against the writer's
    role vivier.
    """
    from django.core.exceptions import ValidationError

    report = get_object_or_404(Report.objects.select_related("game"), pk=pk, game__pk=game_pk)
    if report.author != request.user:
        return HttpResponseForbidden()

    mode = request.POST.get("mode", "add")
    if mode not in _POST_MODES:
        mode = "add"
    status = RapportStatus.DRAFT if mode == "draft" else RapportStatus.PUBLISHED

    actor = _resolve_actor(request)
    try:
        rapport = create_scene_post(
            report=report,
            kind=request.POST.get("kind", ""),
            content=request.POST.get("content", "").strip(),
            actor=actor,
            status=status,
        )
    except ValidationError as exc:
        return HttpResponse("; ".join(exc.messages), status=422)

    if getattr(request, "htmx", False):
        # Inline: fresh composer (#composer) + OOB-append the new post to the fil.
        ctx = _composer_context(request.user, report=report)
        ctx["new_rapport"] = rapport
        return render(request, "games/_composer_after_post.html", ctx)

    return redirect(
        reverse("games:report_edit", kwargs={"game_pk": report.game.pk, "pk": report.pk})
    )


@require_POST
@login_required
def scene_open(request: AuthenticatedRequest, game_pk: str) -> HttpResponse:
    """Open a new scene around a character in the game named in the URL.

    Creates, in one transaction, Report(draft, wall closed) + first Rapport +
    ReportCast(character, role=MAIN) + GameCast(game, character). The
    CharacterAppearance is NOT created eagerly — it is born from the cast at
    publication (publish_report), keeping the temporal wall coherent.

    The game is the one in the URL; the character may be **any** the writer may
    voice there — a character "peut intervenir dans n'importe quelle partie"
    (rule 2b), so it need not originate from this game. The actor is revalidated
    against the role vivier by the service layer.
    """
    from django.core.exceptions import ValidationError

    from suddenly.characters.models import Character

    game = get_object_or_404(Game, pk=game_pk)

    character_slug = request.POST.get("character", "").strip()
    character = get_object_or_404(Character, slug=character_slug)

    actor = _resolve_actor(request)
    mode = request.POST.get("mode", "add")
    status = RapportStatus.DRAFT if mode == "draft" else RapportStatus.PUBLISHED
    try:
        report, _rapport = open_new_scene(
            user=request.user,
            game=game,
            character=character,
            kind=request.POST.get("kind", ""),
            content=request.POST.get("content", "").strip(),
            actor=actor,
            status=status,
        )
    except ValidationError as exc:
        return HttpResponse("; ".join(exc.messages), status=422)

    return redirect(
        reverse("games:report_edit", kwargs={"game_pk": report.game.pk, "pk": report.pk})
    )


def _composer_context(
    user: User,
    *,
    report: Report | None = None,
    game: Game | None = None,
    character: Character | None = None,
    selected_actor: str = "",
    selected_actor_label: str = "",
) -> dict[str, object]:
    """Build the single source of truth the ``_composer.html`` partial consumes.

    Frozen mode (``report`` given): game, personnage and language are inherited
    from the scene — the header is a breadcrumb. Free mode (``report`` absent):
    the header is two selectors and the caller supplies ``games``/``personnages``.

    Either way the role-scoped, non-negotiable pieces are computed here:
    ``is_gm`` (deduced), ``kinds`` (narration only for a GM) and the actor pool.
    """
    from suddenly.characters.models import Character, CharacterStatus

    frozen = report is not None
    if frozen and report is not None:
        game = report.game

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

    own_pcs = Character.objects.filter(owner=user, status=CharacterStatus.PC).order_by("name")

    # Rule 2a: nothing leaves without a personnage AND a partie — drafts too.
    # In frozen mode both are inherited from the scene, so sending is allowed.
    can_send = frozen or (game is not None and character is not None)

    return {
        "report": report,
        "frozen": frozen,
        "game": game,
        "is_gm": is_gm,
        "kinds": kinds,
        "actors": actors,
        "cast_npcs": cast_npcs,
        "own_pcs": own_pcs,
        "selected_character": character,
        "selected_actor": selected_actor,
        "selected_actor_label": selected_actor_label,
        "can_send": can_send,
    }


@login_required
def composer(request: AuthenticatedRequest) -> HttpResponse:
    """The unified post composer, opened from the feed (no frozen scene).

    Two selectors: PERSONNAGE then PARTIE (rule 2b). The game list is **not**
    filtered by the chosen personnage. Choosing a game recomputes role, cast and
    available kinds (rule 2c) — an HTMX GET with ``?region=context`` returns just
    that recomputed region.

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
            )
        except ValidationError as exc:
            return HttpResponse("; ".join(exc.messages), status=422)
        return redirect(
            reverse("games:report_edit", kwargs={"game_pk": report.game.pk, "pk": report.pk})
        )

    ctx = _composer_context(request.user, game=game, character=character)
    ctx["games"] = build_game_queryset(request.user)
    ctx["personnages"] = (
        Character.objects.filter(models.Q(owner=request.user) | models.Q(creator=request.user))
        .select_related("origin_game")
        .order_by("name")
        .distinct()
    )

    if getattr(request, "htmx", False) and request.GET.get("region") == "context":
        return render(request, "games/_composer_context.html", ctx)

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

    ctx = _composer_context(
        request.user,
        report=report,
        game=game,
        selected_actor=npc.slug,
        selected_actor_label=npc.name,
    )
    return render(request, "games/_composer_context.html", ctx)


def _get_authored_rapport(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> Rapport:
    """Fetch a rapport whose scene the caller authored, or raise 404."""
    return get_object_or_404(
        Rapport.objects.select_related("report__game", "report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )


@require_POST
@login_required
def rapport_media_add(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    """Set the single image of a ``description`` rapport (author only).

    One media per description (the OneToOne makes a second one impossible), so
    this endpoint *sets or replaces* rather than appends. Media on a non-
    description kind is refused (422) by ``RapportMedia.clean``.
    """
    from django.core.exceptions import ValidationError

    rapport = _get_authored_rapport(request, game_pk, pk, rapport_pk)
    if rapport.report.author != request.user:
        return HttpResponseForbidden()

    image = request.FILES.get("image")
    if not image:
        return HttpResponse("An image is required.", status=400)

    media = getattr(rapport, "media", None) or RapportMedia(rapport=rapport)
    media.image = image
    media.alt = request.POST.get("alt", "").strip()
    media.tone = request.POST.get("tone", "").strip()
    try:
        media.full_clean()
    except ValidationError as exc:
        return HttpResponse("; ".join(exc.messages), status=422)
    media.save()
    if getattr(request, "htmx", False):
        return render(request, "games/partials/rapport_item.html", {"rapport": rapport})
    return HttpResponse(status=201)


@require_POST
@login_required
def rapport_media_remove(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    """Remove the image of a rapport (author only). Idempotent."""
    rapport = _get_authored_rapport(request, game_pk, pk, rapport_pk)
    if rapport.report.author != request.user:
        return HttpResponseForbidden()
    RapportMedia.objects.filter(rapport=rapport).delete()
    if getattr(request, "htmx", False):
        return render(request, "games/partials/rapport_item.html", {"rapport": rapport})
    return HttpResponse(status=204)


# ---------------------------------------------------------------------------
# Quotes (citations) — the author marks a réplique on a Report they own (§5).
#
# A Quote may be created on a Report not yet released — it simply waits for the
# temporal wall to open before it can be promoted (QuoteQuerySet.promotable).
# Ephemeral visibility is a character-page gesture; here only public/private are
# offered, so the expires_at ⟺ EPHEMERAL constraint is never tripped.
# ---------------------------------------------------------------------------

_QUOTE_VISIBILITIES = frozenset({"public", "private"})


@require_POST
@login_required
def quote_create(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Create a citation on a Report the caller authored. HTMX, returns a card."""
    from suddenly.characters.models import Character, Quote, QuoteVisibility

    report = get_object_or_404(Report.objects.select_related("game"), pk=pk, game__pk=game_pk)
    if report.author != request.user:
        return HttpResponseForbidden()

    content = request.POST.get("content", "").strip()
    if len(content) < 2:
        return HttpResponse("La citation doit faire au moins 2 caractères.", status=422)

    character = get_object_or_404(Character, slug=request.POST.get("character", "").strip())
    visibility = request.POST.get("visibility", QuoteVisibility.PUBLIC)
    if visibility not in _QUOTE_VISIBILITIES:
        visibility = QuoteVisibility.PUBLIC

    quote = Quote.objects.create(
        report=report,
        character=character,
        author=request.user,
        content=content,
        context=request.POST.get("context", "").strip(),
        visibility=visibility,
    )
    return render(request, "quotes/_quote_card.html", {"quote": quote})


@require_POST
@login_required
def quote_delete(
    request: AuthenticatedRequest, game_pk: str, pk: str, quote_pk: str
) -> HttpResponse:
    """Hard-delete a citation of a Report the caller authored (§5)."""
    from suddenly.characters.models import Quote

    quote = get_object_or_404(
        Quote.objects.select_related("report"),
        pk=quote_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )
    if quote.report is None or quote.report.author != request.user:
        return HttpResponseForbidden()
    quote.delete()
    return HttpResponse(status=204)
