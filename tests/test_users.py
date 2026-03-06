"""
Tests for the users app: model constraints, AP URLs, views, and form.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from suddenly.users.models import User
from tests.factories import UserFactory

# ---------------------------------------------------------------------------
# User.email -- unique constraint with null support
# ---------------------------------------------------------------------------


class TestUserEmailConstraint:
    """Two users without email must not conflict (null != null in SQL)."""

    def test_two_null_emails_do_not_conflict(self, db: Any) -> None:
        User.objects.create_user(username="a", password="x", email=None)
        User.objects.create_user(username="b", password="x", email=None)  # must not raise

    def test_two_identical_emails_raise(self, db: Any) -> None:
        User.objects.create_user(username="a", password="x", email="dup@test.com")
        with pytest.raises(Exception):  # IntegrityError wrapped by Django ORM
            User.objects.create_user(username="b", password="x", email="dup@test.com")


# ---------------------------------------------------------------------------
# User.actor_url / actor_inbox / actor_outbox
# ---------------------------------------------------------------------------


class TestUserActorURLs:
    """AP URL properties for local and remote users."""

    def test_local_actor_url(self, user: User, settings: Any) -> None:
        settings.AP_BASE_URL = "https://test.social"
        assert user.actor_url == "https://test.social/users/testuser"

    def test_local_actor_inbox(self, user: User, settings: Any) -> None:
        settings.AP_BASE_URL = "https://test.social"
        assert user.actor_inbox == "https://test.social/users/testuser/inbox"

    def test_local_actor_outbox(self, user: User, settings: Any) -> None:
        settings.AP_BASE_URL = "https://test.social"
        assert user.actor_outbox == "https://test.social/users/testuser/outbox"

    def test_remote_actor_url_returns_ap_id(self, db: Any) -> None:
        remote = User.objects.create_user(
            username="remote",
            password="x",
            remote=True,
            ap_id="https://remote.social/users/alice",
        )
        assert remote.actor_url == "https://remote.social/users/alice"

    def test_remote_actor_url_returns_none_when_ap_id_missing(self, db: Any) -> None:
        remote = User.objects.create_user(username="remote2", password="x", remote=True)
        assert remote.actor_url is None

    def test_remote_actor_inbox_returns_none_when_inbox_url_missing(self, db: Any) -> None:
        remote = User.objects.create_user(username="remote3", password="x", remote=True)
        assert remote.actor_inbox is None

    def test_remote_actor_outbox_returns_none_when_outbox_url_missing(self, db: Any) -> None:
        remote = User.objects.create_user(username="remote4", password="x", remote=True)
        assert remote.actor_outbox is None

    def test_remote_actor_inbox_returns_inbox_url_when_set(self, db: Any) -> None:
        remote = User.objects.create_user(
            username="remote5",
            password="x",
            remote=True,
            inbox_url="https://remote.social/users/alice/inbox",
        )
        assert remote.actor_inbox == "https://remote.social/users/alice/inbox"


# ---------------------------------------------------------------------------
# User.get_absolute_url
# ---------------------------------------------------------------------------


class TestUserGetAbsoluteURL:
    def test_returns_at_prefixed_path(self, user: User) -> None:
        url = user.get_absolute_url()
        assert url == f"/@{user.username}/"


# ---------------------------------------------------------------------------
# User language preference defaults
# ---------------------------------------------------------------------------


class TestUserLanguageDefaults:
    def test_content_language_defaults_to_fr(self, db: Any) -> None:
        u = User.objects.create_user(username="lang", password="x")
        assert u.content_language == "fr"

    def test_preferred_languages_defaults_to_empty_list(self, db: Any) -> None:
        u = User.objects.create_user(username="lang2", password="x")
        assert u.preferred_languages == []


# ---------------------------------------------------------------------------
# ProfileView
# ---------------------------------------------------------------------------


class TestProfileView:
    """GET /@<username>/ -- public profile page."""

    def test_active_user_is_found(self, client: Client, user: User) -> None:
        """Active user exists in queryset -- view proceeds past 404 check."""
        client.raise_request_exception = False
        response = client.get(f"/@{user.username}/")
        assert response.status_code != 404

    def test_inactive_user_returns_404(self, client: Client, db: Any) -> None:
        """is_active=False users are excluded from queryset."""
        client.raise_request_exception = False
        inactive = User.objects.create_user(username="inactive", password="x", is_active=False)
        response = client.get(f"/@{inactive.username}/")
        assert response.status_code == 404

    def test_nonexistent_username_returns_404(self, client: Client, db: Any) -> None:
        client.raise_request_exception = False
        response = client.get("/@nobody_at_all/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# ProfileEditView
# ---------------------------------------------------------------------------


class TestProfileEditView:
    """GET/POST /@<username>/edit/ -- authenticated profile editor."""

    def test_anonymous_redirects_to_login(self, client: Client, user: User) -> None:
        response = client.get(f"/@{user.username}/edit/")
        assert response.status_code == 302
        assert "/accounts/" in response["Location"]

    def test_username_mismatch_redirects_to_own_edit_url(
        self, client: Client, user: User, other_user: User
    ) -> None:
        """Visiting @other/edit/ while logged in as self -> redirected to own edit URL."""
        client.force_login(user)
        response = client.get(f"/@{other_user.username}/edit/")
        assert response.status_code == 302
        assert user.username in response["Location"]
        assert other_user.username not in response["Location"]

    def test_correct_username_passes_dispatch(self, client: Client, user: User) -> None:
        """Authenticated user on their own URL bypasses redirect logic."""
        client.raise_request_exception = False
        client.force_login(user)
        response = client.get(f"/@{user.username}/edit/")
        # Not a login redirect -- dispatch reached the view
        location = response.get("Location", "")
        assert "/accounts/" not in location


# ---------------------------------------------------------------------------
# ProfileForm
# ---------------------------------------------------------------------------


class TestProfileForm:
    """ProfileForm.clean_preferred_languages contract."""

    def test_empty_preferred_languages_returns_empty_list(self, db: Any, user: User) -> None:
        from suddenly.users.forms import ProfileForm

        form = ProfileForm(
            data={
                "display_name": "Test",
                "bio": "",
                "content_language": "fr",
                "preferred_languages": "[]",
                "show_unlabeled_content": True,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["preferred_languages"] == []

    def test_valid_list_passes_through_unchanged(self, db: Any, user: User) -> None:
        from suddenly.users.forms import ProfileForm

        form = ProfileForm(
            data={
                "display_name": "Test",
                "bio": "",
                "content_language": "fr",
                "preferred_languages": '["fr", "en"]',
                "show_unlabeled_content": True,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["preferred_languages"] == ["fr", "en"]


# ---------------------------------------------------------------------------
# Signup -- AP initialization via signal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSignupAPInitialization:
    """Signup creates a local user with ActivityPub fields initialized."""

    def test_signup_creates_user_with_ap_fields(self, client: Client) -> None:
        response = client.post(
            "/accounts/signup/",
            {
                "username": "newplayer",
                "email": "newplayer@example.com",
                "password1": "Str0ngP@ssword!",
                "password2": "Str0ngP@ssword!",
            },
        )
        assert response.status_code == 302

        user = User.objects.get(username="newplayer")
        expected_ap_id = f"{settings.AP_BASE_URL}/users/newplayer"

        assert user.ap_id == expected_ap_id
        assert user.public_key.startswith("-----BEGIN PUBLIC KEY-----")
        assert user.private_key.startswith("-----BEGIN PRIVATE KEY-----")
        assert user.inbox_url == f"{expected_ap_id}/inbox"
        assert user.outbox_url == f"{expected_ap_id}/outbox"
        assert user.remote is False

    def test_signup_with_duplicate_username_fails(self, client: Client) -> None:
        UserFactory(username="taken")  # type: ignore[no-untyped-call]
        count_before = User.objects.count()

        response = client.post(
            "/accounts/signup/",
            {
                "username": "taken",
                "email": "unique@example.com",
                "password1": "Str0ngP@ssword!",
                "password2": "Str0ngP@ssword!",
            },
        )
        assert response.status_code == 200
        assert User.objects.count() == count_before

    def test_signup_with_duplicate_email_fails(self, client: Client) -> None:
        UserFactory(email="taken@example.com")  # type: ignore[no-untyped-call]
        count_before = User.objects.count()

        response = client.post(
            "/accounts/signup/",
            {
                "username": "uniqueuser",
                "email": "taken@example.com",
                "password1": "Str0ngP@ssword!",
                "password2": "Str0ngP@ssword!",
            },
        )
        assert response.status_code == 200
        assert User.objects.count() == count_before

    def test_signup_with_weak_password_fails(self, client: Client) -> None:
        count_before = User.objects.count()

        response = client.post(
            "/accounts/signup/",
            {
                "username": "weakuser",
                "email": "weak@example.com",
                "password1": "123",
                "password2": "123",
            },
        )
        assert response.status_code == 200
        assert User.objects.count() == count_before


# ---------------------------------------------------------------------------
# Remote user -- no keys
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRemoteUserNoKeys:
    """Remote users created via factory have no RSA keys."""

    def test_remote_user_has_no_keys(self) -> None:
        remote: Any = UserFactory(remote=True)  # type: ignore[no-untyped-call]
        assert not remote.public_key
        assert not remote.private_key


# ---------------------------------------------------------------------------
# Factory smoke test
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUserFactorySmoke:
    """Basic factory sanity checks."""

    def test_batch_creates_unique_users(self) -> None:
        users: list[Any] = UserFactory.create_batch(5)
        usernames = {u.username for u in users}
        emails = {u.email for u in users}
        assert len(usernames) == 5
        assert len(emails) == 5


# ---------------------------------------------------------------------------
# E2E placeholder
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_signup_journey() -> None:
    """Full registration journey -- to be implemented with Playwright."""
    pytest.skip("Playwright not configured yet")
