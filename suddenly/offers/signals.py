"""
Django signals for the offers app.

DEC-B3 — one idempotent post_save receiver per carrier type: when a carrier
crosses into a terminal state for its seam, close every ``open``
``SocialOffer`` pointing at it (``OfferService.expire_for_carrier`` handles
the idempotence — safe to call on every save). Connected in
``OffersConfig.ready()``.

Phase 3 adds follower-notification receivers (DEC-B5) alongside these.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="games.Report")
def expire_offer_on_report_release(
    sender: type, instance: Any, created: bool, **kwargs: Any
) -> None:
    """Seam 1 (summary): terminal once the scene is released (crosses the wall)."""
    if instance.released_at is None:
        return

    from suddenly.offers.services import OfferService

    OfferService.expire_for_carrier(instance)


@receiver(post_save, sender="characters.LinkRequest")
def expire_offer_on_link_request_resolved(
    sender: type, instance: Any, created: bool, **kwargs: Any
) -> None:
    """Seam 2 (link_analysis): terminal on ACCEPTED/REJECTED/CANCELLED/EXPIRED."""
    if created:
        return

    from suddenly.characters.models import LinkRequestStatus
    from suddenly.offers.services import OfferService

    terminal = {
        LinkRequestStatus.ACCEPTED,
        LinkRequestStatus.REJECTED,
        LinkRequestStatus.CANCELLED,
        LinkRequestStatus.EXPIRED,
    }
    if instance.status in terminal:
        OfferService.expire_for_carrier(instance)


@receiver(post_save, sender="characters.SharedSequence")
def expire_offer_on_sequence_published(
    sender: type, instance: Any, created: bool, **kwargs: Any
) -> None:
    """Seam 3 (sequence_opening): terminal once the sequence is published."""
    if created:
        return

    from suddenly.characters.models import SharedSequenceStatus
    from suddenly.offers.services import OfferService

    if instance.status == SharedSequenceStatus.PUBLISHED:
        OfferService.expire_for_carrier(instance)
