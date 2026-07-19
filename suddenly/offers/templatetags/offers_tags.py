"""
Template tags for the offers app (Epic B, #132, Phase 3).
"""

from __future__ import annotations

from typing import Any

from django import template

from suddenly.offers.services import OfferService

register = template.Library()


@register.inclusion_tag("offers/_offer_panel.html")
def offer_panel(offer: Any, user: Any) -> dict[str, Any]:
    """Render the Offer panel for ``offer`` from ``user``'s point of view.

    Used by the 3 seam templates (link_request_accept_form / _accept_form,
    sequence_edit, report_detail) so none of them recomputes the
    emitter/follower/resolved branching already centralized in
    ``OfferService.panel_context`` (dry-refactor Rule of Three).
    """
    return OfferService.panel_context(offer=offer, user=user)
