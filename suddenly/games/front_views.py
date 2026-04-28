"""
HTMX-first views for games and reports (DA-1).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from .models import Game, Report, ReportStatus, ReportVisibility


def game_list(request: HttpRequest) -> HttpResponse:
    """Game list with filters (US-02)."""
    from django.db.models import Count, Q

    public_filter = Q(is_public=True, remote=False)
    if request.user.is_authenticated:
        public_filter |= Q(owner=request.user, remote=False)

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

    system = request.GET.get("system", "").strip()
    if system:
        qs = qs.filter(game_system__icontains=system)

    return htmx_render(
        request,
        full_template="games/list.html",
        partial_template="games/_list_results.html",
        context={"games": qs[:24], "system_filter": system},
    )


def game_detail(request: HttpRequest, pk: str) -> HttpResponse:
    """Game detail with reports and characters (US-02)."""
    from django.db.models import Q

    visibility = Q(is_public=True)
    if request.user.is_authenticated:
        visibility |= Q(owner=request.user)

    game = get_object_or_404(Game.objects.select_related("owner").filter(visibility), pk=pk)

    reports = (
        game.reports.filter(status=ReportStatus.PUBLISHED)
        .select_related("author")
        .order_by("-published_at")[:20]
    )
    characters = game.characters.select_related("creator", "owner").order_by("-created_at")[:12]

    return htmx_render(
        request,
        full_template="games/detail.html",
        partial_template="games/detail.html",
        context={
            "game": game,
            "reports": reports,
            "characters": characters,
            "is_owner": request.user == game.owner if request.user.is_authenticated else False,
        },
    )


@login_required
def game_create(request: AuthenticatedRequest) -> HttpResponse:
    """Create a new game (US-02)."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        game_system = request.POST.get("game_system", "").strip()
        is_public = request.POST.get("is_public") == "on"

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

        game = Game.objects.create(
            title=title,
            description=description,
            game_system=game_system,
            is_public=is_public,
            owner=request.user,
        )
        return redirect(reverse("games:detail", kwargs={"pk": game.pk}))

    return htmx_render(
        request,
        full_template="games/game_form.html",
        partial_template="games/game_form.html",
        context={"game": None, "is_public_checked": True},
    )


def report_detail(request: HttpRequest, game_pk: str, pk: str) -> HttpResponse:
    """Report detail page (US-04)."""
    report = get_object_or_404(
        Report.objects.select_related("game", "author"),
        pk=pk,
        game_id=game_pk,
    )

    # Only published reports visible (or own drafts)
    if report.status != ReportStatus.PUBLISHED:
        if not request.user.is_authenticated or request.user != report.author:
            from django.http import Http404

            raise Http404

    cast = report.character_appearances.select_related("character").order_by("role")
    quotes = report.quotes.filter(visibility="public").order_by("-created_at")[:5]

    return htmx_render(
        request,
        full_template="games/report_detail.html",
        partial_template="games/report_detail.html",
        context={
            "report": report,
            "game": report.game,
            "cast": cast,
            "quotes": quotes,
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
                full_template="games/report_create.html",
                partial_template="games/report_create.html",
                context={
                    "game": game,
                    "error": "Le contenu est obligatoire.",
                    "form_data": request.POST,
                },
            )

        report = Report.objects.create(
            title=title,
            content=content,
            content_warning=cw,
            visibility=visibility,
            game=game,
            author=request.user,
            status=ReportStatus.DRAFT,
        )

        if action == "publish":
            from django.utils import timezone

            report.status = ReportStatus.PUBLISHED
            report.published_at = timezone.now()
            report.save()

        return redirect(
            reverse(
                "games:report_detail",
                kwargs={"game_pk": game.pk, "pk": report.pk},
            )
        )

    return htmx_render(
        request,
        full_template="games/report_create.html",
        partial_template="games/report_create.html",
        context={
            "game": game,
            "visibilities": ReportVisibility.choices,
        },
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
        game.save()
        return redirect(reverse("games:detail", kwargs={"pk": game.pk}))

    return htmx_render(
        request,
        full_template="games/game_form.html",
        partial_template="games/game_form.html",
        context={"game": game, "is_public_checked": game.is_public},
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
