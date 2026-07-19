"""
OfferService — business logic for social Offers (Epic B, #132).

DEC-B2/B3/B4: open a SocialOffer on a carrier (Report/LinkRequest/
SharedSequence), record follower responses, accept one (materializing a
literal Rapport on all 3 seams and declining siblings), decline one, and
expire every open Offer once its carrier reaches a terminal state for its
seam. All mutations run inside ``transaction.atomic`` with
``select_for_update`` on the Offer (never inline in a view/signal/handler,
per 03-django-services).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from suddenly.characters.models import LinkRequest, SharedSequence
from suddenly.games.models import RapportKind, RapportStatus, Report, ReportStatus
from suddenly.games.services import create_scene_post

from .models import OfferKind, OfferResponse, OfferResponseStatus, OfferStatus, SocialOffer

if TYPE_CHECKING:
    from django.db.models import Model


def _content_type_for(carrier: Model) -> ContentType:
    return ContentType.objects.get_for_model(carrier)


class OfferService:
    """Business logic for ``SocialOffer`` / ``OfferResponse`` (DEC-B2..B4)."""

    @staticmethod
    def open_offer(*, kind: str, carrier: Model, emitter: Any) -> SocialOffer:
        """Idempotently open (or return the existing) Offer for a carrier.

        Safe to call on every request that renders the carrier's seam (e.g. a
        GET view rendered on every page load): returns the existing ``open``
        offer for ``(carrier, kind)`` instead of creating a duplicate.
        """
        content_type = _content_type_for(carrier)
        existing = SocialOffer.objects.filter(
            content_type=content_type,
            object_id=carrier.pk,
            kind=kind,
            status=OfferStatus.OPEN,
        ).first()
        if existing is not None:
            return existing
        return SocialOffer.objects.create(
            emitter=emitter,
            kind=kind,
            content_type=content_type,
            object_id=carrier.pk,
        )

    @staticmethod
    def respond(*, offer: SocialOffer, responder: Any, content: str) -> OfferResponse:
        """Record a follower's response. One response per ``(offer, responder)``."""
        response, created = OfferResponse.objects.get_or_create(
            offer=offer,
            responder=responder,
            defaults={"content": content},
        )
        if not created and response.status == OfferResponseStatus.PENDING:
            response.content = content
            response.save(update_fields=["content", "updated_at"])
        return response

    @staticmethod
    @transaction.atomic
    def accept_response(response: OfferResponse) -> OfferResponse:
        """Accept one response (DEC-B4): materialize a literal Rapport on all
        3 seams, decline sibling responses, resolve the offer.

        Idempotent: re-accepting an already-accepted response (``created_post``
        already set) returns it unchanged instead of creating a second Rapport.
        """
        offer = SocialOffer.objects.select_for_update().get(pk=response.offer_id)

        if response.status == OfferResponseStatus.ACCEPTED and response.created_post_id:
            return response

        carrier = offer.target
        assert carrier is not None, "Offer target must exist to accept a response"
        report = OfferService._ensure_carrier_report(offer, carrier)

        rapport = create_scene_post(
            report=report,
            kind=RapportKind.NARRATION,
            content=response.content,
            actor=None,
            status=RapportStatus.PUBLISHED,
        )

        if offer.kind == OfferKind.SEQUENCE_OPENING and isinstance(carrier, SharedSequence):
            # Seam 3 also seeds the sequence's own content (DEC-B4).
            carrier.content = response.content
            carrier.save(update_fields=["content", "updated_at"])

        response.status = OfferResponseStatus.ACCEPTED
        response.created_post = rapport
        response.save(update_fields=["status", "created_post", "updated_at"])

        offer.responses.exclude(pk=response.pk).filter(status=OfferResponseStatus.PENDING).update(
            status=OfferResponseStatus.DECLINED
        )

        offer.status = OfferStatus.RESOLVED
        offer.save(update_fields=["status", "updated_at"])

        return response

    @staticmethod
    def decline_response(response: OfferResponse) -> OfferResponse:
        """Decline a single pending response (does not touch the offer or siblings)."""
        if response.status != OfferResponseStatus.PENDING:
            return response
        response.status = OfferResponseStatus.DECLINED
        response.save(update_fields=["status", "updated_at"])
        return response

    @staticmethod
    def _ensure_carrier_report(offer: SocialOffer, carrier: Model) -> Report:
        """Return the Report a ``Rapport`` can be created in for this offer.

        Seam 1 (summary): the carrier IS the Report. Seams 2/3 (link_analysis,
        sequence_opening) have no native scene: fabricate a ``Report`` kept
        ``status=DRAFT`` (DEC-B4 voie (ii)) — invisible everywhere (all
        listings filter ``status=PUBLISHED``; the AP broadcast is gated on
        ``status=="published"``) and requires zero ``games`` migration.
        """
        if offer.kind == OfferKind.SUMMARY:
            assert isinstance(carrier, Report)
            return carrier

        if offer.kind == OfferKind.LINK_ANALYSIS:
            assert isinstance(carrier, LinkRequest)
            character = carrier.target_character
            title = f"Analyse de lien — {character.name}"
        elif offer.kind == OfferKind.SEQUENCE_OPENING:
            assert isinstance(carrier, SharedSequence)
            character = carrier.link.target
            title = f"Ouverture de séquence — {character.name}"
        else:
            raise ValueError(f"Unknown offer kind: {offer.kind}")

        return Report.objects.create(
            game=character.origin_game,
            author=offer.emitter,
            status=ReportStatus.DRAFT,
            title=title,
            content="",
        )

    @staticmethod
    def panel_context(*, offer: SocialOffer | None, user: Any) -> dict[str, Any]:
        """Shared view-context for the Offer panel (dry-refactor Rule of
        Three): a single source of truth consumed both by ``offers/views.py``
        (the standalone panel + HTMX mutation endpoints) and by the
        ``offer_panel`` inclusion tag embedded at the 3 seam templates,
        instead of recomputing the emitter/follower/resolved branching at
        each of the 4 call sites.
        """
        if offer is None:
            return {"offer": None}

        is_authenticated = bool(getattr(user, "is_authenticated", False))
        is_emitter = is_authenticated and user == offer.emitter
        is_resolved = offer.status != OfferStatus.OPEN

        my_response = None
        if is_authenticated and not is_emitter:
            my_response = offer.responses.filter(responder=user).first()

        responses = None
        if is_emitter:
            responses = offer.responses.select_related("responder").order_by("created_at")

        return {
            "offer": offer,
            "is_emitter": is_emitter,
            "is_resolved": is_resolved,
            "my_response": my_response,
            "responses": responses,
        }

    @staticmethod
    @transaction.atomic
    def expire_for_carrier(carrier: Model) -> None:
        """DEC-B3: close every open Offer pointing at a carrier that reached
        a terminal state for its seam.

        Idempotent — filters on ``status=open``, safe to call from a
        post_save receiver on every save of the carrier.
        """
        content_type = _content_type_for(carrier)
        offers = SocialOffer.objects.select_for_update().filter(
            content_type=content_type,
            object_id=carrier.pk,
            status=OfferStatus.OPEN,
        )
        for offer in offers:
            offer.responses.filter(status=OfferResponseStatus.PENDING).update(
                status=OfferResponseStatus.DECLINED
            )
            offer.status = OfferStatus.EXPIRED
            offer.save(update_fields=["status", "updated_at"])
