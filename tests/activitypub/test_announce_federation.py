"""AP federation for the scene Recommend / boost (#155).

A recommendation broadcasts an AP ``Announce`` of the scene to the user's
followers; removing it broadcasts ``Undo(Announce)`` with the same activity id.
Unlike Like (directed to a remote author), a boost is a followers broadcast —
local or remote scene alike.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.activitypub.tasks import send_announce_activity, send_undo_announce_activity
from suddenly.games.models import ReportStatus
from tests.factories import ReportFactory, UserFactory


@pytest.mark.django_db
class TestAnnounceFederationTasks:
    def test_announce_broadcast_for_local_scene(self, mocker: Any) -> None:
        booster = UserFactory()
        report = ReportFactory(
            author=booster, status=ReportStatus.PUBLISHED, visibility="public", remote=False
        )
        spy = mocker.patch("suddenly.activitypub.tasks.broadcast_activity.delay")

        send_announce_activity(str(booster.pk), str(report.pk))

        spy.assert_called_once()
        activity, actor_id, actor_type = spy.call_args.args
        assert activity["type"] == "Announce"
        assert activity["actor"] == booster.actor_url
        assert actor_type == "User"

    def test_undo_announce_references_same_announce_id(self, mocker: Any) -> None:
        booster = UserFactory()
        report = ReportFactory(
            author=booster, status=ReportStatus.PUBLISHED, visibility="public", remote=False
        )
        spy = mocker.patch("suddenly.activitypub.tasks.broadcast_activity.delay")

        send_announce_activity(str(booster.pk), str(report.pk))
        announce = spy.call_args.args[0]
        send_undo_announce_activity(str(booster.pk), str(report.pk))
        undo = spy.call_args.args[0]

        assert undo["type"] == "Undo"
        assert undo["object"]["type"] == "Announce"
        # The Undo wraps the exact Announce id the receiver saw — correlation intact.
        assert undo["object"]["id"] == announce["id"]

    def test_tasks_noop_on_missing_user_or_report(self, mocker: Any) -> None:
        spy = mocker.patch("suddenly.activitypub.tasks.broadcast_activity.delay")

        send_announce_activity(str(uuid.uuid4()), str(uuid.uuid4()))
        send_undo_announce_activity(str(uuid.uuid4()), str(uuid.uuid4()))

        spy.assert_not_called()


@pytest.mark.django_db
class TestRecommendFederationViewWiring:
    def test_view_queues_announce_then_undo(self, client: Client, mocker: Any) -> None:
        booster = UserFactory()
        report = ReportFactory(
            author=booster, status=ReportStatus.PUBLISHED, visibility="public", remote=False
        )
        # feed_views imports `from suddenly.activitypub.signals import _safe_delay`.
        spy = mocker.patch("suddenly.activitypub.signals._safe_delay")
        client.force_login(booster)
        url = reverse("feed:recommend")

        r1 = client.post(url, {"report_id": str(report.pk)})
        assert r1.status_code == 200
        assert spy.call_args.args[0] is send_announce_activity

        r2 = client.post(url, {"report_id": str(report.pk)})
        assert r2.status_code == 200
        assert spy.call_args.args[0] is send_undo_announce_activity
