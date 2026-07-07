"""
HTMX-first views for games and reports (DA-1).
"""

from __future__ import annotations

import datetime
from collections import OrderedDict
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from suddenly.core.models import InstanceSettings
from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

if TYPE_CHECKING:
    from suddenly.users.models import User

from .marker_forms import RapportMarkerForm
from .models import (
    CastRole,
    Game,
    Rapport,
    RapportLink,
    RapportMarker,
    Report,
    ReportCast,
    ReportStatus,
    ReportVisibility,
)
from .rapport_forms import RapportForm
from .services import build_game_queryset, publish_report


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
    """Game detail with reports and characters (US-02)."""
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

    # Only published reports visible (or own drafts)
    if report.status != ReportStatus.PUBLISHED:
        if not request.user.is_authenticated or request.user != report.author:
            raise Http404

    cast = report.character_appearances.select_related("character").order_by("role")
    # Fallback for ingested reports: CharacterAppearance not created via ingest endpoint,
    # so fall back to ReportCast (new_character_name entries) when appearances are absent.
    cast_fallback = report.cast.all() if not cast.exists() else None
    quotes = report.quotes.filter(visibility="public").order_by("-created_at")[:5]

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

    if getattr(request, "htmx", False):
        if mode == "group":
            rapports_qs = (
                report.rapports.select_related("actor")
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
            rapports_qs = report.rapports.select_related("actor").order_by("created_at")
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
            report.rapports.select_related("actor")
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
        rapports_qs = report.rapports.select_related("actor").order_by("created_at")
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
