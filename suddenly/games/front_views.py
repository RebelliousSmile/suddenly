"""
HTMX-first views for games and reports (DA-1).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from suddenly.core.models import InstanceSettings
from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from .models import CastRole, Game, GameSystem, Report, ReportCast, ReportStatus, ReportVisibility
from .services import build_game_queryset


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
            from django.utils import timezone

            report.status = ReportStatus.PUBLISHED
            report.published_at = timezone.now()
            report.save()

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

    game = get_object_or_404(
        Game.objects.select_related("owner", "game_system_ref").filter(visibility), pk=pk
    )

    reports = (
        game.reports.filter(status=ReportStatus.PUBLISHED)
        .select_related("author")
        .order_by("-published_at")[:20]
    )
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

        slug = request.POST.get("game_system_slug", "").strip()
        custom = request.POST.get("game_system_custom", "").strip()
        if slug:
            system_ref = GameSystem.objects.filter(slug=slug, is_deprecated=False).first()
            game_system_text = ""
        else:
            system_ref = None
            game_system_text = custom

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

        cover = request.FILES.get("cover")
        game = Game.objects.create(
            title=title,
            description=description,
            game_system=game_system_text,
            game_system_ref=system_ref,
            is_public=is_public,
            owner=request.user,
            cover=cover,
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
        Report.objects.select_related("game"),
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

        if action == "publish" and report.status != ReportStatus.PUBLISHED:
            from django.utils import timezone

            report.status = ReportStatus.PUBLISHED
            report.published_at = timezone.now()

        report.save(
            update_fields=[
                "title",
                "content",
                "content_warning",
                "visibility",
                "status",
                "published_at",
                "updated_at",
            ]
        )

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
            "form_data": {},
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
        slug = request.POST.get("game_system_slug", "").strip()
        custom = request.POST.get("game_system_custom", "").strip()
        if slug:
            system_ref = GameSystem.objects.filter(slug=slug, is_deprecated=False).first()
            game_system_text = ""
        else:
            system_ref = None
            game_system_text = custom

        game.title = title
        game.description = request.POST.get("description", "").strip()
        game.game_system = game_system_text
        game.game_system_ref = system_ref
        game.is_public = is_public_checked

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
                "game_system_ref",
                "is_public",
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


def game_system_search(request: HttpRequest) -> HttpResponse:
    """HTMX partial: game system autocomplete results."""
    from django.template.loader import render_to_string

    q = request.GET.get("q_system", request.GET.get("q", "")).strip()
    qs = GameSystem.objects.filter(is_deprecated=False).only("slug", "name")
    if q:
        qs = qs.filter(name__icontains=q)
    results = list(qs.order_by("name")[:10])
    html = render_to_string(
        "games/_system_search_results.html",
        {"results": results, "q": q},
        request=request,
    )
    return HttpResponse(html)
