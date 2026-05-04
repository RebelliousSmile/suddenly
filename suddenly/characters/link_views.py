"""
Link request views — flow guide for Adoption/Derivation/Retcon (DA-1).

Wireframe 09-links.md. Uses LinkService for all business logic.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from .models import (
    Character,
    CharacterStatus,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
)
from .services import LinkService


@login_required
def link_choose_type(request: HttpRequest, slug: str) -> HttpResponse:
    """Step 1: Choose link type (Adoption/Derivation/Retcon). US-10."""
    character = get_object_or_404(Character, slug=slug, status=CharacterStatus.NPC)

    # Check if there's already a pending request on this NPC
    has_pending = LinkRequest.objects.filter(
        target_character=character,
        status=LinkRequestStatus.PENDING,
    ).exists()

    return render(
        request,
        "characters/link_choose_type.html",
        {
            "character": character,
            "has_pending": has_pending,
        },
    )


@login_required
def link_request_form(request: AuthenticatedRequest, slug: str, link_type: str) -> HttpResponse:
    """Step 2: Link request form for chosen type. US-10."""
    character = get_object_or_404(Character, slug=slug, status=CharacterStatus.NPC)

    if link_type not in LinkType.values:
        from django.http import Http404

        raise Http404

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        # fork_name included in message for Fork type (stored in LinkRequest.message)
        fork_name = request.POST.get("fork_name", "").strip()  # noqa: F841

        if not message:
            return render(
                request,
                "characters/link_request_form.html",
                {
                    "character": character,
                    "link_type": link_type,
                    "error": "Veuillez expliquer votre proposition narrative.",
                    "form_data": request.POST,
                },
                status=422,
            )

        try:
            link_request = LinkService.create_request(
                requester=request.user,
                target_character=character,
                link_type=link_type,
                message=message,
            )
        except Exception as e:
            return render(
                request,
                "characters/link_request_form.html",
                {
                    "character": character,
                    "link_type": link_type,
                    "error": str(e),
                    "form_data": request.POST,
                },
                status=422,
            )

        queue_position: int | None = None
        if link_request.status == LinkRequestStatus.QUEUED:
            queue_position = LinkService.get_queue_position(link_request)

        return render(
            request,
            "characters/link_request_sent.html",
            {
                "character": character,
                "link_type": link_type,
                "link_request": link_request,
                "queue_position": queue_position,
            },
        )

    return render(
        request,
        "characters/link_request_form.html",
        {"character": character, "link_type": link_type},
    )


@login_required
def link_requests_list(request: AuthenticatedRequest) -> HttpResponse:
    """List received and sent link requests. US-09, US-14."""
    user = request.user
    tab = request.GET.get("tab", "received")

    received = (
        LinkRequest.objects.filter(target_character__creator=user)
        .select_related("requester", "target_character")
        .order_by("-created_at")[:20]
    )
    sent = list(
        LinkRequest.objects.filter(requester=user)
        .select_related("target_character", "target_character__creator")
        .order_by("-created_at")[:20]
    )

    queued_sent = [r for r in sent if r.status == LinkRequestStatus.QUEUED]
    queue_positions: dict[str, int] = {}
    if queued_sent:
        target_ids = [r.target_character_id for r in queued_sent]
        all_queued = list(
            LinkRequest.objects.filter(
                target_character_id__in=target_ids,
                status=LinkRequestStatus.QUEUED,
            ).order_by("target_character_id", "created_at")
        )
        positions_by_target: dict[object, int] = {}
        for lr in all_queued:
            tid = lr.target_character_id
            positions_by_target[tid] = positions_by_target.get(tid, 0) + 1
            queue_positions[str(lr.pk)] = positions_by_target[tid]

    return htmx_render(
        request,
        full_template="characters/link_requests.html",
        partial_template="characters/link_requests.html",
        context={
            "received": received,
            "sent": sent,
            "active_tab": tab,
            "queue_positions": queue_positions,
        },
    )


@login_required
def link_request_accept(request: HttpRequest, pk: str) -> HttpResponse:
    """Accept a link request. US-11, US-14."""
    lr = get_object_or_404(
        LinkRequest,
        pk=pk,
        target_character__creator=request.user,
        status=LinkRequestStatus.PENDING,
    )

    if request.method == "POST":
        response_message = request.POST.get("response_message", "").strip()
        character_link = LinkService.accept_request(lr, response_message=response_message)
        if getattr(request, "htmx", False):
            return render(
                request,
                "characters/_request_resolved.html",
                {
                    "link_request": lr,
                    "shared_sequence": character_link.shared_sequence,
                },
            )
        return render(request, "characters/link_request_accepted.html", {"link_request": lr})

    if getattr(request, "htmx", False):
        return render(request, "characters/_accept_form.html", {"link_request": lr})

    return render(request, "characters/link_request_accept_form.html", {"link_request": lr})


@login_required
def link_request_reject(request: HttpRequest, pk: str) -> HttpResponse:
    """Reject a link request. US-11, US-14."""
    lr = get_object_or_404(
        LinkRequest,
        pk=pk,
        target_character__creator=request.user,
        status=LinkRequestStatus.PENDING,
    )

    if request.method == "POST":
        response_message = request.POST.get("response_message", "").strip()
        LinkService.reject_request(lr, response_message=response_message)
        if getattr(request, "htmx", False):
            return render(request, "characters/_request_resolved.html", {"link_request": lr})
        return redirect(reverse("characters:link_requests"))

    return render(request, "characters/link_request_reject_form.html", {"link_request": lr})


@login_required
def link_request_cancel(request: HttpRequest, pk: str) -> HttpResponse:
    """Cancel own link request. US-15."""
    lr = get_object_or_404(
        LinkRequest,
        pk=pk,
        requester=request.user,
        status__in=[LinkRequestStatus.PENDING, LinkRequestStatus.QUEUED],
    )

    if request.method == "POST":
        service = LinkService()
        service.cancel_request(lr)
        return redirect(reverse("characters:link_requests") + "?tab=sent")

    return redirect(reverse("characters:link_requests") + "?tab=sent")


@login_required
def link_request_card_partial(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Fragment carte d'une demande reçue (HTMX — cancel et rechargements partiels). US-14."""
    lr = get_object_or_404(LinkRequest, pk=pk, target_character__creator=request.user)
    queue_position = LinkService.get_queue_position(lr)
    return render(
        request,
        "characters/_link_request_card_fragment.html",
        {"link_request": lr, "perspective": "received", "queue_position": queue_position},
    )


@login_required
def link_revoke(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Revoke an accepted link (US-16). Creator or adoptant can revoke."""
    from .models import CharacterLink, SharedSequenceStatus

    link = get_object_or_404(
        CharacterLink.objects.select_related(
            "source",
            "target",
            "link_request__requester",
            "shared_sequence",
        ),
        pk=pk,
    )

    # Permission: creator of target character or owner of source
    is_creator = request.user == link.target.creator
    is_owner = link.source.owner and request.user == link.source.owner
    if not is_creator and not is_owner:
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden("Not authorized")

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()

        LinkService.revoke_link(link, reason, request.user)

        return render(
            request,
            "characters/link_revoked.html",
            {"character": link.target, "is_creator": is_creator},
        )

    return render(
        request,
        "characters/link_revoke_form.html",
        {
            "link": link,
            "is_creator": is_creator,
            "has_published_sequence": (
                hasattr(link, "shared_sequence")
                and link.shared_sequence.status == SharedSequenceStatus.PUBLISHED
            ),
        },
    )
