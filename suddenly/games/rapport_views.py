"""
Rapport (post) views: create/edit/delete, markers, replies, media, move,
and quotes (DA-1).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from ._view_helpers import (
    _forbid_non_author,
    _get_scene_rapport,
    _resolve_actor,
    _scene_rapports,
    _user_has_character_in_game,
)
from .marker_forms import RapportMarkerForm
from .models import (
    Rapport,
    RapportLink,
    RapportMarker,
    RapportMedia,
    RapportStatus,
    Report,
)
from .rapport_forms import RapportForm
from .services import (
    build_composer_context,
    move_rapport,
    record_appearance_from_marker,
    update_scene_post,
)

# Public "Citations retenues" visibilities the author may choose from.
_QUOTE_VISIBILITIES = frozenset({"public", "private"})


@login_required
def rapport_create(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    from django.shortcuts import render as _render
    from django.template.loader import render_to_string

    report = get_object_or_404(Report.objects.select_related("game"), pk=pk, game__pk=game_pk)
    if (forbidden := _forbid_non_author(report, request)) is not None:
        return forbidden
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
    """Edit one post. HTMX = the sidebar composer reopens hydrated (edit mode);
    plain requests keep the standalone RapportForm page as a fallback."""
    from django.core.exceptions import ValidationError
    from django.shortcuts import render as _render
    from django.template.loader import render_to_string

    rapport = get_object_or_404(
        Rapport.objects.select_related("report__game", "report__author"),
        pk=rapport_pk,
        report__pk=pk,
        report__game__pk=game_pk,
    )
    if (forbidden := _forbid_non_author(rapport.report, request)) is not None:
        return forbidden

    if request.method == "POST":
        if getattr(request, "htmx", False):
            # Composer edit flow — same field contract as scene_post_create
            # (kind, content, actor as slug). Media/replies keep their own
            # endpoints on the card.
            actor = _resolve_actor(request)
            try:
                update_scene_post(
                    rapport=rapport,
                    kind=request.POST.get("kind", ""),
                    content=request.POST.get("content", "").strip(),
                    actor=actor,
                )
            except ValidationError as exc:
                return HttpResponse("; ".join(exc.messages), status=422)
            # Fresh add-mode composer (main swap) + the updated card OOB.
            ctx = build_composer_context(request.user, report=rapport.report)
            ctx["edited_rapport"] = rapport
            return render(request, "games/_composer_after_edit.html", ctx)

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

    if getattr(request, "htmx", False):
        # The sidebar composer, hydrated for edit — or fresh again on cancel.
        if request.GET.get("cancel"):
            ctx = build_composer_context(request.user, report=rapport.report)
        else:
            ctx = build_composer_context(request.user, report=rapport.report, edit_rapport=rapport)
        return render(request, "games/_composer.html", ctx)

    form = RapportForm(instance=rapport, game=rapport.report.game)
    return _render(request, "games/rapport_form.html", {"form": form, "report": rapport.report})


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
    if (forbidden := _forbid_non_author(rapport.report, request)) is not None:
        return forbidden
    # Federation caution: a released scene has crossed the wall and may be
    # federated — its posts are frozen; a local hard-delete would desync remotes.
    if rapport.report.is_released:
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
    if (forbidden := _forbid_non_author(rapport.report, request)) is not None:
        return forbidden
    if request.method == "POST":
        form = RapportMarkerForm(request.POST, game=rapport.report.game)
        if form.is_valid():
            marker = form.save(commit=False)
            marker.rapport = rapport
            marker.save()
            # A character entrance also records a durable CharacterAppearance.
            record_appearance_from_marker(marker)
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
    if (forbidden := _forbid_non_author(marker.rapport.report, request)) is not None:
        return forbidden
    if request.method == "POST":
        marker.delete()
    return HttpResponse("")


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
    from django.core.exceptions import ValidationError
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

    if (forbidden := _forbid_non_author(rapport.report, request)) is not None:
        return forbidden

    parent_iri = request.POST.get("parent_iri", "").strip()
    validate_url = URLValidator()

    try:
        validate_url(parent_iri)
    except ValidationError:
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

    rapport = _get_scene_rapport(request, game_pk, pk, rapport_pk)
    if (forbidden := _forbid_non_author(rapport.report, request)) is not None:
        return forbidden

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
    rapport = _get_scene_rapport(request, game_pk, pk, rapport_pk)
    if (forbidden := _forbid_non_author(rapport.report, request)) is not None:
        return forbidden
    RapportMedia.objects.filter(rapport=rapport).delete()
    if getattr(request, "htmx", False):
        return render(request, "games/partials/rapport_item.html", {"rapport": rapport})
    return HttpResponse(status=204)


@require_POST
@login_required
def rapport_move(
    request: AuthenticatedRequest, game_pk: str, pk: str, rapport_pk: str
) -> HttpResponse:
    """Reorder a Rapport up/down in the scene (author only, while not released).

    Returns the re-rendered fil (#rapports-list) so the swap shows at once. The
    sequence is frozen once the scene has crossed the wall.
    """
    rapport = _get_scene_rapport(request, game_pk, pk, rapport_pk)
    if (forbidden := _forbid_non_author(rapport.report, request)) is not None:
        return forbidden
    if rapport.report.is_released:
        return HttpResponse("The sequence is frozen once the scene is shared.", status=400)

    direction = request.POST.get("direction", "up")
    if direction not in ("up", "down"):
        direction = "up"
    move_rapport(report=rapport.report, rapport=rapport, direction=direction)

    return render(
        request,
        "games/partials/_rapports_list.html",
        {"rapports": _scene_rapports(rapport.report)},
    )


# ---------------------------------------------------------------------------
# Quotes (citations) — the author marks a réplique on a Report they own (§5).
#
# A Quote may be created on a Report not yet released — it simply waits for the
# temporal wall to open before it can be promoted (QuoteQuerySet.promotable).
# Ephemeral visibility is a character-page gesture; here only public/private are
# offered, so the expires_at ⟺ EPHEMERAL constraint is never tripped.
# ---------------------------------------------------------------------------


@require_POST
@login_required
def quote_create(request: AuthenticatedRequest, game_pk: str, pk: str) -> HttpResponse:
    """Create a citation on a Report the caller authored. HTMX, returns a card."""
    from suddenly.characters.models import Character, Quote, QuoteVisibility

    report = get_object_or_404(Report.objects.select_related("game"), pk=pk, game__pk=game_pk)
    if (forbidden := _forbid_non_author(report, request)) is not None:
        return forbidden

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
    if (forbidden := _forbid_non_author(quote.report, request)) is not None:
        return forbidden
    quote.delete()
    return HttpResponse(status=204)
