"""Unit tests for fediverse_auth.services."""

from __future__ import annotations

import pytest

from suddenly.fediverse_auth import services
from suddenly.fediverse_auth.models import FediverseAccount, FediverseApp
from suddenly.users.models import User


class TestNormalizeInstance:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("mastodon.social", "mastodon.social"),
            ("  MASTODON.social  ", "mastodon.social"),
            ("https://mastodon.social/", "mastodon.social"),
            ("https://mastodon.social/@alice", "mastodon.social"),
            ("@alice@mastodon.social", "mastodon.social"),
            ("alice@mastodon.social", "mastodon.social"),
            ("piaille.fr/web", "piaille.fr"),
            ("sub.example.co.uk", "sub.example.co.uk"),
        ],
    )
    def test_valid(self, raw: str, expected: str) -> None:
        assert services.normalize_instance(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", "not a host", "localhost", "http://", "@@@", "a"])
    def test_invalid(self, raw: str) -> None:
        with pytest.raises(services.InvalidInstanceError):
            services.normalize_instance(raw)


@pytest.mark.django_db
class TestGetOrRegisterApp:
    def test_registers_once_and_caches(self, mocker) -> None:
        mocker.patch.object(services.client, "detect_software", return_value="mastodon")
        reg = mocker.patch.object(
            services.client,
            "register_app",
            return_value={"client_id": "cid", "client_secret": "secret"},
        )
        redirect = "https://suddenly.test/accounts/fediverse/callback/"

        app1 = services.get_or_register_app("mastodon.social", redirect)
        app2 = services.get_or_register_app("mastodon.social", redirect)

        assert app1.pk == app2.pk
        assert app1.client_id == "cid"
        assert reg.call_count == 1  # second call served from cache
        assert FediverseApp.objects.count() == 1

    def test_rejects_unsupported_software(self, mocker) -> None:
        mocker.patch.object(services.client, "detect_software", return_value="lemmy")
        with pytest.raises(services.client.FediverseClientError):
            services.get_or_register_app(
                "lemmy.world", "https://suddenly.test/accounts/fediverse/callback/"
            )


@pytest.mark.django_db
class TestResolveOrCreateUser:
    def _account(self, **over) -> dict:
        base = {
            "id": "12345",
            "username": "alice",
            "acct": "alice",
            "display_name": "Alice",
            "url": "https://mastodon.social/@alice",
        }
        base.update(over)
        return base

    def test_creates_new_local_user(self) -> None:
        user, created = services.resolve_or_create_user(
            "mastodon.social", self._account(), registrations_open=True
        )
        assert created is True
        assert user.username == "alice"
        assert user.email is None
        assert not user.has_usable_password()
        fa = FediverseAccount.objects.get(instance="mastodon.social", uid="12345")
        assert fa.user == user
        assert fa.acct == "alice@mastodon.social"

    def test_returns_existing_link(self) -> None:
        user, _ = services.resolve_or_create_user(
            "mastodon.social", self._account(), registrations_open=True
        )
        again, created = services.resolve_or_create_user(
            "mastodon.social", self._account(display_name="Alice v2"), registrations_open=True
        )
        assert created is False
        assert again.pk == user.pk
        assert User.objects.count() == 1

    def test_username_collision_is_suffixed(self) -> None:
        User.objects.create_user(username="alice", email="a@example.com", password="x")
        user, created = services.resolve_or_create_user(
            "mastodon.social", self._account(), registrations_open=True
        )
        assert created is True
        assert user.username == "alice_2"

    def test_registration_closed_blocks_new_user(self) -> None:
        with pytest.raises(PermissionError):
            services.resolve_or_create_user(
                "mastodon.social", self._account(), registrations_open=False
            )
        assert User.objects.count() == 0

    def test_no_email_takeover(self) -> None:
        """Provisioning must never adopt an existing user by email."""
        victim = User.objects.create_user(
            username="victim", email="alice@mastodon.social", password="secret"
        )
        user, created = services.resolve_or_create_user(
            "mastodon.social",
            self._account(username="alice"),
            registrations_open=True,
        )
        assert created is True
        assert user.pk != victim.pk

    def test_same_username_different_instance_are_distinct_users(self) -> None:
        u1, _ = services.resolve_or_create_user(
            "mastodon.social", self._account(), registrations_open=True
        )
        u2, created = services.resolve_or_create_user(
            "piaille.fr", self._account(), registrations_open=True
        )
        assert created is True
        assert u1.pk != u2.pk
        assert FediverseAccount.objects.count() == 2
