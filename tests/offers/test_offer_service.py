"""Tests for OfferService — social Offers replacing Muses (Epic B, #132).

Covers the service invariants on the SUMMARY seam (carrier IS a Report):
idempotent open, one response per responder, accept materializes a Rapport +
declines siblings + resolves the offer (idempotent), decline, and expiry.
"""

from __future__ import annotations

from typing import Any

import pytest

from suddenly.games.models import Report
from suddenly.offers.models import (
    OfferKind,
    OfferResponseStatus,
    OfferStatus,
    SocialOffer,
)
from suddenly.offers.services import OfferService
from suddenly.users.models import User
from tests.factories import UserFactory


@pytest.fixture
def responder(db: Any) -> User:
    return UserFactory(  # type: ignore[return-value,no-untyped-call]
        username="responder", email="responder@example.com"
    )


@pytest.fixture
def responder2(db: Any) -> User:
    return UserFactory(  # type: ignore[return-value,no-untyped-call]
        username="responder2", email="responder2@example.com"
    )


@pytest.mark.django_db
class TestOpenOffer:
    def test_open_is_idempotent(self, user: User, report: Report) -> None:
        first = OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=user)
        second = OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=user)
        assert first.pk == second.pk
        assert SocialOffer.objects.count() == 1
        assert first.status == OfferStatus.OPEN


@pytest.mark.django_db
class TestRespond:
    def test_one_response_per_responder(self, user: User, report: Report, responder: User) -> None:
        offer = OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=user)
        r1 = OfferService.respond(offer=offer, responder=responder, content="première")
        r2 = OfferService.respond(offer=offer, responder=responder, content="corrigée")
        assert r1.pk == r2.pk
        r2.refresh_from_db()
        assert r2.content == "corrigée"
        assert offer.responses.count() == 1


@pytest.mark.django_db
class TestAcceptResponse:
    def test_accept_materializes_post_declines_siblings_resolves(
        self, user: User, report: Report, responder: User, responder2: User
    ) -> None:
        offer = OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=user)
        chosen = OfferService.respond(offer=offer, responder=responder, content="le bon texte")
        sibling = OfferService.respond(offer=offer, responder=responder2, content="autre")

        accepted = OfferService.accept_response(chosen)

        assert accepted.status == OfferResponseStatus.ACCEPTED
        assert accepted.created_post is not None
        assert accepted.created_post.content == "le bon texte"

        sibling.refresh_from_db()
        assert sibling.status == OfferResponseStatus.DECLINED

        offer.refresh_from_db()
        assert offer.status == OfferStatus.RESOLVED

    def test_accept_is_idempotent(self, user: User, report: Report, responder: User) -> None:
        offer = OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=user)
        chosen = OfferService.respond(offer=offer, responder=responder, content="texte")
        first = OfferService.accept_response(chosen)
        post_pk = first.created_post_id
        second = OfferService.accept_response(chosen)
        assert second.created_post_id == post_pk
        assert report.rapports.count() == 1


@pytest.mark.django_db
class TestDeclineAndExpire:
    def test_decline_pending_response(self, user: User, report: Report, responder: User) -> None:
        offer = OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=user)
        resp = OfferService.respond(offer=offer, responder=responder, content="texte")
        OfferService.decline_response(resp)
        resp.refresh_from_db()
        assert resp.status == OfferResponseStatus.DECLINED

    def test_expire_for_carrier_closes_open_offers(
        self, user: User, report: Report, responder: User
    ) -> None:
        offer = OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=user)
        resp = OfferService.respond(offer=offer, responder=responder, content="texte")
        OfferService.expire_for_carrier(report)
        offer.refresh_from_db()
        resp.refresh_from_db()
        assert offer.status == OfferStatus.EXPIRED
        assert resp.status == OfferResponseStatus.DECLINED
