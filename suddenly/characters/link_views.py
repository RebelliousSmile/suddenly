"""
Link request views — flow guide for Adoption/Derivation/Retcon (DA-1).

Wireframe 09-links.md. Uses LinkService for all business logic.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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
def link_request_form(request: HttpRequest, slug: str, link_type: str) -> HttpResponse:
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
            service = LinkService()
            service.create_request(
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

        return render(
            request,
            "characters/link_request_sent.html",
            {"character": character, "link_type": link_type},
        )

    return render(
        request,
        "characters/link_request_form.html",
        {"character": character, "link_type": link_type},
    )


@login_required
def link_requests_list(request: HttpRequest) -> HttpResponse:
    """List received and sent link requests. US-09, US-14."""
    user = request.user
    tab = request.GET.get("tab", "received")

    received = (
        LinkRequest.objects.filter(target_character__creator=user)
        .select_related("requester", "target_character")
        .order_by("-created_at")[:20]
    )
    sent = (
        LinkRequest.objects.filter(requester=user)
        .select_related("target_character", "target_character__creator")
        .order_by("-created_at")[:20]
    )

    return htmx_render(
        request,
        full_template="characters/link_requests.html",
        partial_template="characters/link_requests.html",
        context={
            "received": received,
            "sent": sent,
            "active_tab": tab,
        },
    )


@login_required
def link_request_accept(request: HttpRequest, pk: str) -> HttpResponse:
    """Accept a link request. US-11."""
    lr = get_object_or_404(
        LinkRequest,
        pk=pk,
        target_character__creator=request.user,
        status=LinkRequestStatus.PENDING,
    )

    if request.method == "POST":
        response_message = request.POST.get("response_message", "").strip()
        service = LinkService()
        service.accept_request(lr, response_message=response_message)
        return render(
            request,
            "characters/link_request_accepted.html",
            {"link_request": lr},
        )

    return render(
        request,
        "characters/link_request_accept_form.html",
        {"link_request": lr},
    )


@login_required
def link_request_reject(request: HttpRequest, pk: str) -> HttpResponse:
    """Reject a link request. US-11."""
    lr = get_object_or_404(
        LinkRequest,
        pk=pk,
        target_character__creator=request.user,
        status=LinkRequestStatus.PENDING,
    )

    if request.method == "POST":
        response_message = request.POST.get("response_message", "").strip()
        service = LinkService()
        service.reject_request(lr, response_message=response_message)
        return redirect(reverse("characters:link_requests"))

    return render(
        request,
        "characters/link_request_reject_form.html",
        {"link_request": lr},
    )


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
