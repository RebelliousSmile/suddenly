"""
Report (scene) views: compose, release, edit, cast and scene-post gestures (DA-1).
"""

from __future__ import annotations

import datetime

from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from suddenly.core.models import InstanceSettings
from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from ._view_helpers import (
    _POST_MODES,
    _forbid_non_author,
    _resolve_actor,
    _scene_cast,
    _scene_rapports,
)
from .models import (
    CastRole,
    Game,
    Rapport,
    RapportStatus,
    Report,
    ReportCast,
    ReportStatus,
    ReportVisibility,
)
from .services import (
    annotate_viewer_reactions,
    build_composer_context,
    can_edit_scene,
    close_scene,
    create_scene_post,
    fiction_continuations,
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


def report_detail(request: HttpRequest, game_pk: str, pk: str) -> HttpResponse:
    """Report detail page (US-04)."""
    # Annotate the viewer's like/recommend state (#155) so the scene page can
    # render the engagement buttons hot — set-based, no extra per-request query
    # for anonymous visitors (helper is a no-op then).
    report_qs = annotate_viewer_reactions(
        Report.objects.select_related("game", "author", "previous_report").prefetch_related(
            "rapports__parent_links",
            "rapports__parent_links__parent_rapport",
            "next_reports",
        ),
        request.user,
    )
    report = get_object_or_404(report_qs, pk=pk, game_id=game_pk)

    # Wall check (SUD-V2): a report must be BOTH published (federation axis)
    # AND released (liberation axis) to be visible to the public. A report that
    # is published but not yet released is still a game in progress behind the
    # wall — only its editors (author or GM) may read it.
    if (report.status != ReportStatus.PUBLISHED or not report.is_released) and not can_edit_scene(
        request.user, report
    ):
        raise Http404

    from suddenly.characters.models import Character, Quote

    cast = report.character_appearances.select_related("character").order_by("role")
    # Fallback for ingested reports: CharacterAppearance not created via ingest endpoint,
    # so fall back to ReportCast (new_character_name entries) when appearances are absent.
    cast_fallback = report.cast.all() if not cast.exists() else None

    # Public "Citations retenues": the double lock, never re-expressed here.
    quotes = Quote.objects.promotable().filter(report=report).order_by("-created_at")[:5]

    # Draft rapports are private to their editors: an editor (author or GM)
    # manages them here (edit/publish), but the public thread of a released
    # report shows only published rapports (per-rapport wall, decision #1 A).
    is_author = request.user.is_authenticated and request.user == report.author
    can_edit = can_edit_scene(request.user, report)

    # §5: the author marks a réplique as citation. They manage every quote of
    # this report (regardless of the wall), and pick a speaker among its cast.
    manage_quotes = None
    quote_characters = None
    offer = None
    if is_author:
        manage_quotes = report.quotes.select_related("character").order_by("-created_at")
        quote_characters = Character.objects.filter(
            models.Q(appearances__report=report) | models.Q(cast_entries__report=report)
        ).distinct()

        # The seam-1 (summary) social Offer opened at import time, addressed
        # to the author's followers (Epic B, #132). Only the author sees it
        # here — followers reach it via their Notification(type=OFFER) link
        # to the standalone offers:panel page (this page 404s for them while
        # the scene is behind the wall).
        from django.contrib.contenttypes.models import ContentType

        from suddenly.offers.models import OfferKind, SocialOffer

        offer = (
            SocialOffer.objects.filter(
                content_type=ContentType.objects.get_for_model(Report),
                object_id=report.pk,
                kind=OfferKind.SUMMARY,
            )
            .order_by("-created_at")
            .first()
        )

    rapports = report.rapports.select_related("actor").prefetch_related(
        "parent_links__parent_rapport", "markers__character", "media"
    )
    if not can_edit:
        rapports = rapports.filter(status=RapportStatus.PUBLISHED)

    scene_cast = _scene_cast(report)

    # Fiction order: continuations for the closing « Next → » link. Uses the
    # prefetched next_reports (no extra query per item). The opening « Previously »
    # link reads report.previous_report (select_related above); both partials
    # self-guard and store no id.
    fiction_next = fiction_continuations(report)

    # Direct-message entry point (Epic E, #135, DEC-E7) — read-only, gated by
    # mutuality; never writes a Follow. Targets the scene's author.
    dm_recipient = None
    if request.user.is_authenticated and request.user != report.author:
        from suddenly.characters.models import Follow

        if Follow.objects.are_mutual(request.user, report.author):
            dm_recipient = report.author

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
            "can_edit": can_edit,
            "scene_cast": scene_cast,
            "manage_quotes": manage_quotes,
            "quote_characters": quote_characters,
            "rapports": rapports,
            "fiction_next": fiction_next,
            "offer": offer,
            "dm_recipient": dm_recipient,
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
    """Edit an existing scene (author or GM — cf. can_edit_scene)."""
    report = get_object_or_404(
        Report.objects.select_related("game").prefetch_related("cast__character"),
        pk=pk,
        game_id=game_pk,
    )
    if not can_edit_scene(request.user, report):
        raise Http404

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
    rapports = _scene_rapports(report)

    # The scene cast (collapsible box): characters brought in by ReportCast plus
    # anyone who has actually spoken/acted (rapport actors).
    scene_cast = _scene_cast(report)

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
            "scene_cast": scene_cast,
            "can_edit": True,
            # The unified post composer (same _composer.html as the feed), frozen
            # to this scene: game/personnage/language inherited, not editable.
            **build_composer_context(request.user, report=report),
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

    # Only the game master may introduce a brand-new NPC. Adding an existing
    # character to the cast stays open to the scene author.
    if new_name and not character and not is_game_master(request.user, report.game):
        return HttpResponseForbidden("Only the game master can create a new NPC.")

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
    if (forbidden := _forbid_non_author(report, request)) is not None:
        return forbidden

    mode = request.POST.get("mode", "add")
    if mode not in _POST_MODES:
        mode = "add"
    status = RapportStatus.DRAFT if mode == "draft" else RapportStatus.PUBLISHED

    actor = _resolve_actor(request)

    # Optional reply target (discussion): a Rapport of this scene, or a fed. IRI.
    reply_parent = None
    reply_local = request.POST.get("reply_local", "").strip()
    if reply_local:
        reply_parent = get_object_or_404(Rapport, pk=reply_local, report=report)

    try:
        rapport = create_scene_post(
            report=report,
            kind=request.POST.get("kind", ""),
            content=request.POST.get("content", "").strip(),
            actor=actor,
            status=status,
            reply_parent=reply_parent,
            reply_iri=request.POST.get("reply_iri", ""),
            image=request.FILES.get("image"),
            media_alt=request.POST.get("media_alt", ""),
        )
    except ValidationError as exc:
        return HttpResponse("; ".join(exc.messages), status=422)

    if getattr(request, "htmx", False):
        # Inline: fresh composer (#composer) + OOB-append the new post to the fil.
        ctx = build_composer_context(request.user, report=report)
        ctx["new_rapport"] = rapport
        response = render(request, "games/_composer_after_post.html", ctx)
        # Canonical htmx client event → the overlay (if any) closes on it. More
        # robust than sniffing the swap target on an outerHTML swap.
        response["HX-Trigger"] = "composer-posted"
        return response

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
