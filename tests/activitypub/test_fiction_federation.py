"""Fiction-order federation — emission (soft IRI) and wired reception.

Emission: ``serialize_report`` adds ``previousReport`` / ``temporal*`` as soft IRIs
under the ``suddenly:`` namespace; a hard FK never crosses federation. Reception:
``_handle_create_report`` ingests a remote ``Create(Article)`` idempotently and
resolves the IRI to a FK when the anchor is already known (clearing the IRI — XOR).

No network: remote authors are pre-seeded in the DB so ``get_or_create_remote_user``
takes its fast path.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import pytest
from django.conf import settings

from suddenly.activitypub.inbox import _handle_create_report, handle_create
from suddenly.activitypub.serializers import serialize_report
from suddenly.games.models import Report, ReportTemporalKind, ReportVisibility
from suddenly.users.models import User
from tests.factories import GameFactory, ReportFactory

ACTOR_URL = "https://peer.example/users/alice"
GAME_IRI = "https://peer.example/games/1"


def _remote_author(actor_url: str = ACTOR_URL) -> User:
    return User.objects.create(  # type: ignore[no-untyped-call]
        username=f"alice@{urlparse(actor_url).netloc}",
        ap_id=actor_url,
        remote=True,
    )


def _article(**overrides: Any) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "type": "Article",
        "id": "https://peer.example/reports/1",
        "attributedTo": ACTOR_URL,
        "context": GAME_IRI,
        "name": "Remote scene",
        "content": "Body of the remote scene.",
        "published": "2026-07-15T10:00:00+00:00",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
    }
    obj.update(overrides)
    return obj


def _create_activity(obj: dict[str, Any]) -> dict[str, Any]:
    return {"type": "Create", "actor": ACTOR_URL, "object": obj}


def _local_prefix(report: Report) -> str:
    return f"https://{settings.DOMAIN}/reports/{report.pk}"


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestSerialize:
    def test_context_declares_fiction_vocabulary(self) -> None:
        data = serialize_report(ReportFactory())
        vocab = next(c for c in data["@context"] if isinstance(c, dict))
        for term in ("previousReport", "temporalKind", "temporalAnchor", "temporalLabel"):
            assert vocab[term] == f"suddenly:{term}"

    def test_serialize_local_chained_emits_predecessor_iri(self) -> None:
        game = GameFactory()
        a = ReportFactory(game=game)
        b = ReportFactory(game=game, previous_report=a)
        data = serialize_report(b)
        assert data["previousReport"] == _local_prefix(a)

    def test_serialize_remote_chained_uses_soft_iri(self) -> None:
        iri = "https://peer.example/reports/prev"
        b = ReportFactory(previous_report_iri=iri)
        data = serialize_report(b)
        assert data["previousReport"] == iri

    def test_serialize_normal_omits_fiction_keys(self) -> None:
        data = serialize_report(ReportFactory())
        assert "previousReport" not in data
        assert "temporalKind" not in data
        assert "temporalAnchor" not in data

    def test_serialize_flashback_emits_temporal_block(self) -> None:
        game = GameFactory()
        anchor = ReportFactory(game=game)
        b = ReportFactory(
            game=game,
            previous_report=anchor,
            temporal_kind=ReportTemporalKind.FLASHBACK,
            temporal_anchor=anchor,
            temporal_label="Ten years earlier",
        )
        data = serialize_report(b)
        assert data["temporalKind"] == "flashback"
        assert data["temporalAnchor"] == _local_prefix(anchor)
        assert data["temporalLabel"] == "Ten years earlier"


# ---------------------------------------------------------------------------
# Reception (wired)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestReceive:
    def test_receive_create_article_ingests_report(self) -> None:
        author = _remote_author()
        handle_create(_create_activity(_article()), "game", "x")
        report = Report.objects.get(ap_id="https://peer.example/reports/1")
        assert report.remote is True
        assert report.author_id == author.pk
        assert report.game.ap_id == GAME_IRI
        assert report.visibility == ReportVisibility.PUBLIC
        assert report.published_at is not None

    def test_ingest_is_idempotent_on_double_post(self) -> None:
        _remote_author()
        obj = _article()
        _handle_create_report(_create_activity(obj), obj)
        _handle_create_report(_create_activity(obj), obj)
        assert Report.objects.filter(ap_id="https://peer.example/reports/1").count() == 1

    def test_receive_resolves_known_iri_to_fk_and_clears_iri(self) -> None:
        _remote_author()
        anchor = ReportFactory(remote=True, ap_id="https://peer.example/reports/anchor")
        obj = _article(previousReport="https://peer.example/reports/anchor")
        _handle_create_report(_create_activity(obj), obj)
        report = Report.objects.get(ap_id="https://peer.example/reports/1")
        assert report.previous_report_id == anchor.pk
        assert not report.previous_report_iri  # XOR: FK linked ⟹ IRI cleared

    def test_receive_unknown_anchor_keeps_soft_iri(self) -> None:
        _remote_author()
        unknown = "https://peer.example/reports/unknown"
        obj = _article(temporalAnchor=unknown, temporalKind="flashback")
        _handle_create_report(_create_activity(obj), obj)
        report = Report.objects.get(ap_id="https://peer.example/reports/1")
        assert report.temporal_anchor_id is None
        assert report.temporal_anchor_iri == unknown
        assert report.temporal_kind == ReportTemporalKind.FLASHBACK

    def test_receive_absent_fiction_block_chains_nothing(self) -> None:
        _remote_author()
        obj = _article()
        _handle_create_report(_create_activity(obj), obj)
        report = Report.objects.get(ap_id="https://peer.example/reports/1")
        assert report.previous_report_id is None
        assert not report.previous_report_iri

    def test_receive_expanded_term_is_tolerated(self) -> None:
        _remote_author()
        anchor = ReportFactory(remote=True, ap_id="https://peer.example/reports/anchor")
        obj = _article()
        obj["suddenly:previousReport"] = "https://peer.example/reports/anchor"
        _handle_create_report(_create_activity(obj), obj)
        report = Report.objects.get(ap_id="https://peer.example/reports/1")
        assert report.previous_report_id == anchor.pk

    def test_ingest_numqueries_is_bounded(self, django_assert_max_num_queries: Any) -> None:
        # The ingestion cost is a fixed constant (dedup + author + game + create +
        # link resolution, plus per-object signal side effects) — it does NOT grow
        # with the data. The generous constant bound only asserts the absence of an
        # N+1 loop, not a precise count.
        _remote_author()
        obj = _article()
        with django_assert_max_num_queries(25):
            _handle_create_report(_create_activity(obj), obj)
