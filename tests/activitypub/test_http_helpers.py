"""
Regression tests for the canonical federation-core helpers in ``_http.py``
(audit rows 2, 4 — Phase 2 of the code-quality corrections plan).

Covers the three risks flagged in the plan's risk register:
- remote-user ingest is idempotent (no duplicate row, no re-fetch on replay)
- ``sign_and_deliver`` hands ``deliver_activity.delay`` the exact same
  keyword-argument contract as before the refactor (unchanged headers/signature)
- an unusually long remote handle truncates instead of raising ``DataError``
"""

from __future__ import annotations

from typing import Any

import pytest

from suddenly.activitypub._http import get_or_create_remote_user, sign_and_deliver
from tests.factories import UserFactory


@pytest.mark.django_db
class TestGetOrCreateRemoteUserIdempotent:
    def test_second_call_reuses_existing_row_without_refetch(self, mocker: Any) -> None:
        actor_url = "https://remote.example/users/alice"
        fetch_mock = mocker.patch(
            "suddenly.activitypub._http.fetch_ap_actor",
            return_value={
                "preferredUsername": "alice",
                "name": "Alice",
                "summary": "hi",
                "inbox": f"{actor_url}/inbox",
                "outbox": f"{actor_url}/outbox",
                "publicKey": {"publicKeyPem": "PEM-DATA"},
            },
        )

        first = get_or_create_remote_user(actor_url)
        assert first is not None
        user1, created1 = first
        assert created1 is True
        assert fetch_mock.call_count == 1

        second = get_or_create_remote_user(actor_url)
        assert second is not None
        user2, created2 = second
        assert created2 is False
        assert user2.pk == user1.pk
        # DB-first fast path: no second HTTP fetch on replay.
        assert fetch_mock.call_count == 1


@pytest.mark.django_db
class TestSignAndDeliverSpy:
    def test_calls_deliver_activity_with_unchanged_signed_kwargs(self, mocker: Any) -> None:
        # UserFactory doesn't trigger `user_signed_up` (allauth-only signal, see
        # `suddenly/users/signals.py`), so the private key must be set directly.
        signer = UserFactory(private_key="TEST-PRIVATE-KEY-PEM-DATA")
        activity = {"type": "Follow", "actor": signer.actor_url, "object": "https://x/1"}
        inbox_url = "https://remote.example/users/bob/inbox"

        captured_calls: list[dict[str, Any]] = []

        def fake_delay(**kwargs: Any) -> None:
            captured_calls.append(kwargs)

        mock_deliver = mocker.MagicMock()
        mock_deliver.delay.side_effect = fake_delay
        # sign_and_deliver lazily imports `from .tasks import deliver_activity` —
        # patch the tasks module attribute, same pattern as existing e2e tests.
        mocker.patch("suddenly.activitypub.tasks.deliver_activity", mock_deliver)

        sign_and_deliver(activity, inbox_url, signer=signer)

        assert len(captured_calls) == 1
        call_kwargs = captured_calls[0]
        assert call_kwargs["activity"] == activity
        assert call_kwargs["inbox_url"] == inbox_url
        assert call_kwargs["actor_key_id"] == f"{signer.actor_url}#main-key"
        assert call_kwargs["private_key_pem"] == signer.private_key

    def test_no_op_when_inbox_url_falsy(self, mocker: Any) -> None:
        signer = UserFactory()
        mock_deliver = mocker.MagicMock()
        mocker.patch("suddenly.activitypub.tasks.deliver_activity", mock_deliver)

        sign_and_deliver({"type": "Follow"}, None, signer=signer)

        mock_deliver.delay.assert_not_called()


@pytest.mark.django_db
class TestGetOrCreateRemoteUserTruncation:
    def test_long_handle_and_domain_truncate_without_crashing(self, mocker: Any) -> None:
        # `ap_id` is a plain URLField (max_length=200, no override for User) —
        # keep the actor_url itself short enough to insert; only the
        # preferredUsername/name need to be long enough to force truncation of
        # `username` (150) / `display_name` (100).
        long_username = "a" * 160
        actor_url = f"https://remote.example/users/{long_username}"

        mocker.patch(
            "suddenly.activitypub._http.fetch_ap_actor",
            return_value={
                "preferredUsername": long_username,
                "name": "c" * 150,
                "summary": "",
                "inbox": f"{actor_url}/inbox",
                "outbox": f"{actor_url}/outbox",
                "publicKey": {"publicKeyPem": "PEM-DATA"},
            },
        )

        result = get_or_create_remote_user(actor_url)

        assert result is not None
        user, created = result
        assert created is True
        assert len(user.username) == 150
        assert len(user.display_name) == 100
