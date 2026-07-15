"""Tests for post-ingestion Muses orchestration (#126).

The task must self-gate on the flag + the author's opt-in, attach the summary
as an editable proposal, notify with a classified link summary, and degrade to
a no-op (no proposal, no notification) when the hub is unavailable.
"""

from __future__ import annotations

from typing import Any

import pytest

from suddenly.core.models import Notification, NotificationType
from suddenly.games.tasks import muses_post_ingest
from suddenly.muses.exceptions import MusesUnavailable
from tests.factories import ReportFactory

pytestmark = pytest.mark.django_db


def _mock_client(mocker: Any, *, enabled: bool = True) -> Any:
    """Patch the MusesClient used by the task and return the instance mock."""
    cls = mocker.patch("suddenly.games.tasks.MusesClient")
    cls.is_enabled.return_value = enabled
    return cls.return_value


def test_stores_summary_and_notifies_when_opted_in(mocker: Any) -> None:
    report = ReportFactory(author__muses_post_ingest_optin=True, content="A scene.")
    inst = _mock_client(mocker)
    inst.analyze.side_effect = [
        {"summary": "A resolved tale."},
        {"links": [{"strength": "strong"}, {"strength": "medium"}, {"strength": "weak"}]},
    ]

    result = muses_post_ingest(str(report.id))

    report.refresh_from_db()
    assert report.muses_summary_proposal == "A resolved tale."
    notif = Notification.objects.get(
        recipient=report.author, type=NotificationType.MUSES_SUGGESTION
    )
    assert "résumé" in notif.message
    assert "3 ancrage" in notif.message and "1 fort" in notif.message
    assert notif.target == report
    assert result == "done: notified"


def test_noop_when_muses_disabled(mocker: Any) -> None:
    report = ReportFactory(author__muses_post_ingest_optin=True)
    inst = _mock_client(mocker, enabled=False)

    result = muses_post_ingest(str(report.id))

    inst.analyze.assert_not_called()
    report.refresh_from_db()
    assert report.muses_summary_proposal == ""
    assert not Notification.objects.filter(recipient=report.author).exists()
    assert result == "skipped: muses disabled"


def test_noop_when_author_opted_out(mocker: Any) -> None:
    report = ReportFactory(author__muses_post_ingest_optin=False)
    inst = _mock_client(mocker)

    result = muses_post_ingest(str(report.id))

    inst.analyze.assert_not_called()
    assert result == "skipped: author opted out"
    assert not Notification.objects.filter(recipient=report.author).exists()


def test_degrades_when_hub_unavailable(mocker: Any) -> None:
    report = ReportFactory(author__muses_post_ingest_optin=True)
    inst = _mock_client(mocker)
    inst.analyze.side_effect = MusesUnavailable("hub down")

    result = muses_post_ingest(str(report.id))

    report.refresh_from_db()
    assert report.muses_summary_proposal == ""
    assert not Notification.objects.filter(recipient=report.author).exists()
    assert result == "done: no assistance produced"


def test_ingest_endpoint_enqueues_assist(mocker: Any, api_client: Any, settings: Any) -> None:
    """A successful ingest runs the assist task (eager in tests) end to end."""
    from tests.factories import GameFactory

    settings.INGEST_TOKEN = "s3cr3t"
    game = GameFactory(remote=False, owner__muses_post_ingest_optin=True)
    inst = _mock_client(mocker)
    inst.analyze.side_effect = [{"summary": "From import."}, {"links": []}]

    resp = api_client.post(
        "/api/games/reports/ingest/",
        {"game_id": str(game.id), "report": {"resolved": True, "content": "Imported body."}},
        format="json",
        HTTP_X_INGEST_TOKEN="s3cr3t",
    )

    assert resp.status_code == 201
    from suddenly.games.models import Report

    report = Report.objects.get(id=resp.data["id"])
    assert report.muses_summary_proposal == "From import."


def test_partial_success_summary_only(mocker: Any) -> None:
    """Summary succeeds, links call fails: still store the summary and notify."""
    report = ReportFactory(author__muses_post_ingest_optin=True)
    inst = _mock_client(mocker)
    inst.analyze.side_effect = [{"summary": "Kept."}, MusesUnavailable("links down")]

    result = muses_post_ingest(str(report.id))

    report.refresh_from_db()
    assert report.muses_summary_proposal == "Kept."
    notif = Notification.objects.get(recipient=report.author)
    assert "résumé" in notif.message
    assert "ancrage" not in notif.message
    assert result == "done: notified"
