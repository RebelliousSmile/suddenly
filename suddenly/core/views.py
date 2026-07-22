"""
Core views and HTMX helpers.

DA-1: HTMX-first pattern — views return full HTML pages for normal requests
and partial HTML fragments for HTMX requests (detected via django-htmx).
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from suddenly.core.services import (
    get_distinct_tag_names,
    get_instance_stats,
    get_recent_public_reports,
)
from suddenly.core.types import AuthenticatedRequest


def switch_language(request: HttpRequest) -> HttpResponse:
    """Django's ``set_language`` + persistence for authenticated users.

    The switcher cookie is honoured by LocaleMiddleware and respected by
    InstanceLanguageMiddleware (which only supplies the instance *default*).
    For an authenticated user the choice is also saved to
    ``interface_language`` so UserLanguageMiddleware applies it from the very
    next request — otherwise the stored preference would silently override
    every switch.
    """
    from django.conf import settings
    from django.views.i18n import set_language as django_set_language

    response = django_set_language(request)
    user = request.user
    if request.method == "POST" and user.is_authenticated:
        lang = request.POST.get("language", "")
        if lang in dict(settings.LANGUAGES):
            user.interface_language = lang
            user.save(update_fields=["interface_language"])
    return response


def home(request: HttpRequest) -> HttpResponse:
    """
    Home page.

    Mastodon-like behaviour (Front #1): a single canonical ``/`` URL with two
    renders depending on the session. Authenticated users get their feed
    (delegated to ``feed_home``, keeping ``/`` as the displayed URL); anonymous
    visitors get the marketing vitrine enriched with instance stats (Front #2).
    """
    if request.user.is_authenticated:
        from suddenly.core.feed_views import feed_home

        return feed_home(cast(AuthenticatedRequest, request))

    return render(
        request,
        "core/home.html",
        {
            "recent_reports": get_recent_public_reports(),
            "stats": get_instance_stats(),
        },
    )


def popular_scenes(request: HttpRequest) -> HttpResponse:
    """Public wall of the most-liked released scenes (/populaires) — no auth.

    Substitute for the retired citations wall (#146): ranks released scenes by
    total likes (all-time). The wall filter stays in ``most_liked()`` — this view
    never re-expresses it. Infinite scroll: an HTMX ``?page=N`` request (fired by
    the sentinel) returns the items partial alone, which swaps itself for the
    next batch + a fresh sentinel.
    """
    from suddenly.core.services import popular_scenes_page

    page_obj = popular_scenes_page(request.GET.get("page"), user=request.user)
    template = (
        "core/_popular_scenes_items.html"
        if getattr(request, "htmx", False)
        else "core/popular_scenes.html"
    )
    return render(
        request,
        template,
        {"page_obj": page_obj, "scenes": page_obj.object_list},
    )


def explorer(request: HttpRequest) -> HttpResponse:
    """Public discovery page — characters and games tabs."""
    from suddenly.characters.models import Character, CharacterStatus
    from suddenly.characters.services import build_character_queryset
    from suddenly.games.models import Game
    from suddenly.games.services import build_game_queryset

    tab = request.GET.get("tab", "characters")
    context: dict[str, Any] = {"active_tab": tab}

    if tab == "games":
        games_qs = build_game_queryset(
            user=request.user,
            q=request.GET.get("q", ""),
            system=request.GET.get("system", ""),
            tag=request.GET.get("tag", ""),
        )
        context.update(
            {
                "games": games_qs[:24],
                "system_filter": request.GET.get("system", ""),
                "active_tag": request.GET.get("tag", ""),
                "all_tags": get_distinct_tag_names(Game),
                "query": request.GET.get("q", ""),
            }
        )
    else:
        chars_qs = build_character_queryset(
            q=request.GET.get("q", ""),
            status=request.GET.get("status", ""),
            tag=request.GET.get("tag", ""),
        )
        context.update(
            {
                "characters": chars_qs[:24],
                "query": request.GET.get("q", ""),
                "status_filter": request.GET.get("status", ""),
                "active_tag": request.GET.get("tag", ""),
                "all_tags": get_distinct_tag_names(Character),
                "statuses": CharacterStatus.choices,
            }
        )

    return render(request, "core/explorer.html", context)


def about(request: HttpRequest) -> HttpResponse:
    """Instance about page (US-31, wireframe 17)."""
    return render(request, "core/about.html", {"stats": get_instance_stats()})


def directory(request: HttpRequest) -> HttpResponse:
    """Public profile directory — local, active members of this instance.

    Remote (federated) accounts are excluded: they are discovered through
    federation, not listed as members here.
    """
    from suddenly.users.models import User

    members = User.objects.filter(remote=False, is_active=True).order_by("display_name", "username")
    paginator = Paginator(members, 24)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/directory.html",
        {"page_obj": page_obj, "total": paginator.count},
    )


@login_required
def report_user(request: HttpRequest, username: str) -> HttpResponse:
    """Report a user to instance admins (#136, DEC-F1).

    GET renders the "Report this user" form; POST files the signalement via
    ``core.moderation.create_user_report``. Self-report is rejected as a
    form error rather than a hard 400, since a user can always reach their
    own profile URL directly. Mirrors the GET/POST-in-one-view pattern used
    by ``instance_settings`` (form re-render + ``messages`` on error,
    redirect on success) rather than the HTMX 3-template inline pattern,
    since this is a standalone navigation target, not a list-item action.
    """
    from suddenly.core.models import ReportCategory
    from suddenly.core.moderation import create_user_report
    from suddenly.users.models import User

    reported_user = get_object_or_404(User, username=username)

    if request.method == "POST":
        category = request.POST.get("category", "")
        comment = request.POST.get("comment", "").strip()
        valid_categories = {choice for choice, _label in ReportCategory.choices}

        if category not in valid_categories:
            messages.error(request, _("Please select a reason."))
        else:
            try:
                create_user_report(
                    reporter=cast(AuthenticatedRequest, request).user,
                    reported_user=reported_user,
                    category=category,
                    comment=comment,
                )
            except ValueError:
                messages.error(request, _("You cannot report yourself."))
            else:
                messages.success(request, _("Report submitted. An admin will review it."))
                return redirect(reported_user.get_absolute_url())

    return render(
        request,
        "core/report_user_form.html",
        {
            "reported_user": reported_user,
            "categories": ReportCategory.choices,
        },
    )


#: Whitelisted reportable content kinds (#150). Anything else → 404.
_REPORTABLE_KINDS = ("character", "scene", "game")


def _resolve_reportable(kind: str, pk: str) -> tuple[Any, Any, str, Any]:
    """Resolve a content ``kind``+``pk`` to ``(target, author, back_url, label)``.

    Whitelisted local content only (character / scene / game) — an unknown kind
    or remote content raises ``Http404`` (remote content is not locally
    moderatable, and the ban acts on a local user). ``author`` is the person a
    signalement is filed against; ``back_url`` is the content's detail page.
    """
    from django.urls import reverse

    if kind == "character":
        from suddenly.characters.models import Character

        character = get_object_or_404(Character, pk=pk, remote=False)
        author = character.owner or character.creator
        back = reverse("characters:detail", kwargs={"slug": character.slug})
        return character, author, back, character.name
    if kind == "scene":
        from suddenly.games.models import Report

        scene = get_object_or_404(Report, pk=pk, remote=False)
        back = reverse("games:report_detail", kwargs={"game_pk": scene.game_id, "pk": scene.pk})
        return scene, scene.author, back, scene.title or _("an untitled scene")
    if kind == "game":
        from suddenly.games.models import Game

        game = get_object_or_404(Game, pk=pk, remote=False)
        back = reverse("games:detail", kwargs={"pk": game.pk})
        return game, game.owner, back, game.title
    raise Http404("Unknown reportable content kind")


@login_required
def report_content(request: HttpRequest, kind: str, pk: str) -> HttpResponse:
    """Report a piece of content — character, scene, or game — to admins (#150).

    Option A: reuses the person-report pipeline (``UserReport`` + the existing
    moderation queue) rather than a parallel ``ContentReport`` system. Files a
    signalement against the content's author with the content itself recorded
    as the report's GFK context, so the admin queue can link straight to the
    flagged element. Self-reports and remote content are refused; the reported
    author is never notified (DEC-F6).
    """
    from suddenly.core.models import ReportCategory
    from suddenly.core.moderation import create_user_report

    target, author, back_url, label = _resolve_reportable(kind, pk)
    user = cast(AuthenticatedRequest, request).user

    if author is None or author.pk == user.pk:
        messages.error(request, _("You cannot report your own content."))
        return redirect(back_url)

    if request.method == "POST":
        category = request.POST.get("category", "")
        comment = request.POST.get("comment", "").strip()
        valid_categories = {choice for choice, _label in ReportCategory.choices}

        if category not in valid_categories:
            messages.error(request, _("Please select a reason."))
        else:
            create_user_report(
                reporter=user,
                reported_user=author,
                category=category,
                comment=comment,
                context=target,
            )
            messages.success(request, _("Report submitted. An admin will review it."))
            return redirect(back_url)

    return render(
        request,
        "core/report_content_form.html",
        {
            "target_label": label,
            "cancel_url": back_url,
            "categories": ReportCategory.choices,
        },
    )


def privacy(request: HttpRequest) -> HttpResponse:
    """Privacy policy — static content page."""
    return render(request, "core/privacy.html")


def apps(request: HttpRequest) -> HttpResponse:
    """Compatible applications — static content page for the Fediverse."""
    return render(request, "core/apps.html")


def shortcuts(request: HttpRequest) -> HttpResponse:
    """Keyboard shortcuts reference — mirrors the global handler in main.js."""
    return render(request, "core/shortcuts.html")


def htmx_render(
    request: HttpRequest,
    full_template: str,
    partial_template: str,
    context: dict[str, Any] | None = None,
) -> HttpResponse:
    """Render full page or HTMX partial based on request type.

    DA-1 pattern: if the request comes from HTMX (hx-get/hx-post),
    return the partial template (fragment). Otherwise return the full
    page that wraps the partial.

    Usage in views:
        return htmx_render(
            request,
            full_template="characters/list.html",
            partial_template="characters/_list_results.html",
            context={"characters": qs},
        )
    """
    template = partial_template if getattr(request, "htmx", False) else full_template
    return render(request, template, context or {})
