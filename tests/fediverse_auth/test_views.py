"""Integration tests for the fediverse login views."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.fediverse_auth import views
from suddenly.fediverse_auth.models import FediverseAccount, FediverseApp
from suddenly.users.models import User

CALLBACK = "http://localhost:8000/accounts/fediverse/callback/"


@pytest.fixture
def app(db) -> FediverseApp:
    return FediverseApp.objects.create(
        instance="mastodon.social",
        software="mastodon",
        client_id="cid",
        client_secret="secret",
        redirect_uri=CALLBACK,
    )


@pytest.mark.django_db
class TestLoginView:
    def test_get_renders_form(self) -> None:
        r = Client().get(reverse("fediverse_auth:login"))
        assert r.status_code == 200
        assert b'name="instance"' in r.content

    def test_disabled_returns_404(self, settings) -> None:
        settings.FEDIVERSE_LOGIN_ENABLED = False
        assert Client().get(reverse("fediverse_auth:login")).status_code == 404

    def test_invalid_instance_returns_400(self) -> None:
        r = Client().post(reverse("fediverse_auth:login"), {"instance": "not a host"})
        assert r.status_code == 400

    def test_post_redirects_to_authorize_and_sets_state(self, mocker) -> None:
        mocker.patch.object(views.services.client, "detect_software", return_value="mastodon")
        mocker.patch.object(
            views.services.client,
            "register_app",
            return_value={"client_id": "cid", "client_secret": "secret"},
        )
        c = Client()
        r = c.post(reverse("fediverse_auth:login"), {"instance": "mastodon.social"})
        assert r.status_code == 302
        assert "https://mastodon.social/oauth/authorize?" in r["Location"]
        flow = c.session["fediverse_oauth"]
        assert flow["instance"] == "mastodon.social"
        assert flow["action"] == "login"
        assert flow["state"] in r["Location"]

    def test_remote_failure_returns_502(self, mocker) -> None:
        mocker.patch.object(views.services.client, "detect_software", return_value="")
        mocker.patch.object(
            views.services.client,
            "register_app",
            side_effect=views.client.FediverseClientError("boom"),
        )
        r = Client().post(reverse("fediverse_auth:login"), {"instance": "mastodon.social"})
        assert r.status_code == 502


@pytest.mark.django_db
class TestCallbackView:
    ACCOUNT = {
        "id": "999",
        "username": "bob",
        "acct": "bob",
        "display_name": "Bob",
        "url": "https://mastodon.social/@bob",
    }

    def _prime_session(self, client: Client, **flow) -> None:
        session = client.session
        session["fediverse_oauth"] = {
            "state": "st-123",
            "instance": "mastodon.social",
            "next": "/",
            "action": "login",
            **flow,
        }
        session.save()

    def test_new_user_logged_in(self, app, mocker) -> None:
        mocker.patch.object(views.client, "exchange_code", return_value="tok")
        mocker.patch.object(views.client, "verify_credentials", return_value=self.ACCOUNT)
        c = Client()
        self._prime_session(c)
        r = c.get(reverse("fediverse_auth:callback"), {"code": "abc", "state": "st-123"})
        assert r.status_code == 302
        assert r["Location"] == "/"
        user = User.objects.get(username="bob")
        assert FediverseAccount.objects.filter(user=user, uid="999").exists()
        assert c.session.get("_auth_user_id") == str(user.pk)

    def test_state_mismatch_rejected(self, app, mocker) -> None:
        exch = mocker.patch.object(views.client, "exchange_code")
        c = Client()
        self._prime_session(c)
        r = c.get(reverse("fediverse_auth:callback"), {"code": "abc", "state": "WRONG"})
        assert r.status_code == 302
        assert reverse("account_login") in r["Location"]
        exch.assert_not_called()
        assert User.objects.filter(username="bob").count() == 0

    def test_missing_session_redirects(self) -> None:
        r = Client().get(reverse("fediverse_auth:callback"), {"code": "abc", "state": "x"})
        assert r.status_code == 302
        assert reverse("account_login") in r["Location"]

    def test_provider_error_redirects(self, app) -> None:
        c = Client()
        self._prime_session(c)
        r = c.get(reverse("fediverse_auth:callback"), {"error": "access_denied", "state": "st-123"})
        assert r.status_code == 302
        assert reverse("account_login") in r["Location"]

    def test_connect_links_to_current_user(self, app, mocker) -> None:
        mocker.patch.object(views.client, "exchange_code", return_value="tok")
        mocker.patch.object(views.client, "verify_credentials", return_value=self.ACCOUNT)
        user = User.objects.create_user(
            username="carol", email="c@example.com", password="pw12345!"
        )
        c = Client()
        c.force_login(user)
        self._prime_session(c, action="connect")
        before = User.objects.count()
        r = c.get(reverse("fediverse_auth:callback"), {"code": "abc", "state": "st-123"})
        assert r.status_code == 302
        assert User.objects.count() == before  # no new user provisioned
        assert FediverseAccount.objects.get(uid="999").user == user

    def test_registration_closed_blocks_new(self, app, mocker) -> None:
        from suddenly.core.models import InstanceSettings

        s = InstanceSettings.get()
        s.registrations_open = False
        s.save()
        mocker.patch.object(views.client, "exchange_code", return_value="tok")
        mocker.patch.object(views.client, "verify_credentials", return_value=self.ACCOUNT)
        c = Client()
        self._prime_session(c)
        r = c.get(reverse("fediverse_auth:callback"), {"code": "abc", "state": "st-123"})
        assert r.status_code == 302
        assert reverse("account_login") in r["Location"]
        assert not User.objects.filter(username="bob").exists()


@pytest.mark.django_db
def test_login_page_shows_fediverse_button() -> None:
    r = Client().get(reverse("account_login"))
    assert r.status_code == 200
    assert b"Se connecter avec le Fediverse" in r.content
