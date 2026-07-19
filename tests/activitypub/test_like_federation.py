"""AP federation for the scene Like (#138, part 2).

A like on a *remote* scene emits a directed AP ``Like`` to the remote actor's
inbox; an unlike emits ``Undo(Like)`` with the same Like ``id``. A like on a
*local* scene emits nothing.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.activitypub.tasks import send_like_activity, send_undo_like_activity
from suddenly.games.models import Report, ReportStatus
from tests.factories import GameFactory, ReportFactory, UserFactory


def _remote_report(**kwargs: Any) -> Report:
    """A published remote scene whose author is a remote actor with an inbox."""
    remote_author = UserFactory(
        remote=True,
        ap_id="https://remote.example/users/alice",
        inbox_url="https://remote.example/users/alice/inbox",
    )
    return ReportFactory(
        author=remote_author,
        game=GameFactory(owner=remote_author),
        status=ReportStatus.PUBLISHED,
        visibility="public",
        remote=True,
        ap_id="https://remote.example/reports/xyz",
        **kwargs,
    )


@pytest.mark.django_db
class TestLikeFederationTasks:
    def test_like_activity_delivered_to_remote_actor(self, mocker: Any) -> None:
        liker = UserFactory(private_key="TEST-KEY")
        report = _remote_report()
        # send_like_activity lazily imports `from ._http import sign_and_deliver`.
        spy = mocker.patch("suddenly.activitypub._http.sign_and_deliver")

        send_like_activity(str(liker.pk), str(report.pk))

        spy.assert_called_once()
        activity, inbox_url = spy.call_args.args
        assert spy.call_args.kwargs["signer"] == liker
        assert activity["type"] == "Like"
        assert activity["actor"] == liker.actor_url
        assert activity["object"] == report.ap_id
        assert inbox_url == report.author.actor_inbox

    def test_like_activity_noop_on_local_scene(self, mocker: Any) -> None:
        liker = UserFactory()
        local_report = ReportFactory(status=ReportStatus.PUBLISHED, remote=False)
        spy = mocker.patch("suddenly.activitypub._http.sign_and_deliver")

        send_like_activity(str(liker.pk), str(local_report.pk))

        spy.assert_not_called()

    def test_undo_like_references_same_like_id(self, mocker: Any) -> None:
        liker = UserFactory(private_key="TEST-KEY")
        report = _remote_report()
        spy = mocker.patch("suddenly.activitypub._http.sign_and_deliver")

        send_like_activity(str(liker.pk), str(report.pk))
        like_activity = spy.call_args.args[0]
        send_undo_like_activity(str(liker.pk), str(report.pk))
        undo_activity = spy.call_args.args[0]

        assert undo_activity["type"] == "Undo"
        assert undo_activity["object"]["type"] == "Like"
        # The Undo wraps the exact Like id the receiver saw — correlation intact.
        assert undo_activity["object"]["id"] == like_activity["id"]
        assert undo_activity["object"]["object"] == report.ap_id

    def test_undo_like_noop_on_local_scene(self, mocker: Any) -> None:
        liker = UserFactory()
        local_report = ReportFactory(status=ReportStatus.PUBLISHED, remote=False)
        spy = mocker.patch("suddenly.activitypub._http.sign_and_deliver")

        send_undo_like_activity(str(liker.pk), str(local_report.pk))

        spy.assert_not_called()


@pytest.mark.django_db
class TestLikeFederationViewWiring:
    def test_view_queues_like_then_undo_on_remote_scene(self, client: Client, mocker: Any) -> None:
        liker = UserFactory()
        report = _remote_report()
        # feed_views imports `from suddenly.activitypub.signals import _safe_delay`.
        spy = mocker.patch("suddenly.activitypub.signals._safe_delay")
        client.force_login(liker)
        url = reverse("feed:like")

        r1 = client.post(url, {"report_id": str(report.pk)})
        assert r1.status_code == 200
        assert spy.call_args.args[0] is send_like_activity

        r2 = client.post(url, {"report_id": str(report.pk)})
        assert r2.status_code == 200
        assert spy.call_args.args[0] is send_undo_like_activity

    def test_view_no_federation_on_local_scene(self, client: Client, mocker: Any) -> None:
        liker = UserFactory()
        local_report = ReportFactory(
            author=liker, status=ReportStatus.PUBLISHED, visibility="public", remote=False
        )
        spy = mocker.patch("suddenly.activitypub.signals._safe_delay")
        client.force_login(liker)

        resp = client.post(reverse("feed:like"), {"report_id": str(local_report.pk)})
        assert resp.status_code == 200
        spy.assert_not_called()
