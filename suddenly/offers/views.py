"""
HTMX views for the offers app (Epic B, #132, Phase 3).

3-template pattern (03-htmx-patterns.md): every mutating POST (respond /
accept / decline) re-renders the ``_offer_panel.html`` fragment in place,
which itself dispatches between "open, I'm the emitter" / "open, I can
respond" / "resolved" (``OfferService.panel_context``).

``offer_panel`` (GET) is a standalone, login-only page — not gated by the
carrier's own visibility rules. The 3 seam pages (report_detail,
link_request_accept, sequence_edit) are gated to the emitter/narrow
participants and cannot serve as the surface a general follower reaches
from their ``Notification(type=OFFER)`` link, so this route exists
alongside the inline panel embedded on the seam pages for the emitter's own
view.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import OfferResponse, SocialOffer
from .services import OfferService


@login_required
def offer_panel(request: HttpRequest, pk: str) -> HttpResponse:
    """Standalone Offer panel page."""
    offer = get_object_or_404(SocialOffer, pk=pk)
    context = OfferService.panel_context(offer=offer, user=request.user)
    return render(request, "offers/panel.html", context)


@login_required
@require_POST
def offer_respond(request: HttpRequest, pk: str) -> HttpResponse:
    """A follower submits (or edits, while still pending) their response."""
    offer = get_object_or_404(SocialOffer, pk=pk)
    content = request.POST.get("content", "").strip()
    if content:
        OfferService.respond(offer=offer, responder=request.user, content=content)
    context = OfferService.panel_context(offer=offer, user=request.user)
    return render(request, "offers/_offer_panel.html", context)


@login_required
@require_POST
def offer_accept(request: HttpRequest, pk: str) -> HttpResponse:
    """Emitter accepts one response — materializes a Rapport, declines siblings."""
    response = get_object_or_404(OfferResponse.objects.select_related("offer"), pk=pk)
    if request.user != response.offer.emitter:
        raise Http404
    OfferService.accept_response(response)
    context = OfferService.panel_context(offer=response.offer, user=request.user)
    return render(request, "offers/_offer_panel.html", context)


@login_required
@require_POST
def offer_decline(request: HttpRequest, pk: str) -> HttpResponse:
    """Emitter declines a single pending response."""
    response = get_object_or_404(OfferResponse.objects.select_related("offer"), pk=pk)
    if request.user != response.offer.emitter:
        raise Http404
    OfferService.decline_response(response)
    context = OfferService.panel_context(offer=response.offer, user=request.user)
    return render(request, "offers/_offer_panel.html", context)
