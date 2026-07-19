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


@receiver(post_save, sender="offers.SocialOffer")
def notify_followers_on_offer_created(
    sender: type, instance: Any, created: bool, **kwargs: Any
) -> None:
    """DEC-B5: notify the emitter's local followers when a SocialOffer opens.

    Remote followers are reached via the Offer AP activity instead (Phase 4);
    this only creates in-app Notifications for local followers. Fires
    regardless of the emitter's own locality (a mirrored remote emitter's
    local followers still need the local notification — DEC-B6).
    """
    if not created:
        return

    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow
    from suddenly.core.models import Notification, NotificationType
    from suddenly.users.models import User

    user_ct = ContentType.objects.get_for_model(User)
    offer_ct = ContentType.objects.get_for_model(instance)
    follower_ids = Follow.objects.filter(
        content_type=user_ct, object_id=instance.emitter_id, follower__remote=False
    ).values_list("follower_id", flat=True)

    for fid in follower_ids:
        if fid == instance.emitter_id:
            continue
        Notification.objects.create(
            recipient_id=fid,
            type=NotificationType.OFFER,
            actor=instance.emitter,
            target_content_type=offer_ct,
            target_object_id=instance.pk,
            message=f"@{instance.emitter.username} a une nouvelle offre à laquelle répondre",
        )


@receiver(post_save, sender="offers.OfferResponse")
def notify_emitter_on_offer_response(
    sender: type, instance: Any, created: bool, **kwargs: Any
) -> None:
    """DEC-B5: notify the offer's emitter when a follower responds.

    Interpretation of DEC-B5's wording: ``OFFER_RESPONSE``'s fixed label
    ("Votre offre a reçu une réponse") only makes sense addressed to the
    emitter, so this fires on response creation rather than on acceptance.
    Skipped when the emitter is a mirrored remote user (no local session to
    read it — their own instance notifies them via the Accept/Reject AP
    round-trip instead, DEC-B6/Phase 4).
    """
    if not created:
        return

    from django.contrib.contenttypes.models import ContentType

    from suddenly.core.models import Notification, NotificationType

    offer = instance.offer
    if offer.emitter.remote or offer.emitter_id == instance.responder_id:
        return

    Notification.objects.create(
        recipient=offer.emitter,
        type=NotificationType.OFFER_RESPONSE,
        actor=instance.responder,
        target_content_type=ContentType.objects.get_for_model(offer),
        target_object_id=offer.pk,
        message=f"@{instance.responder.username} a répondu à votre offre",
    )
