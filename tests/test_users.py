"""
Tests for the users app: model constraints, AP URLs, views, and form.
"""

import pytest

from suddenly.users.models import User


# ---------------------------------------------------------------------------
# User.email — unique constraint with null support
# ---------------------------------------------------------------------------


class TestUserEmailConstraint:
    """Two users without email must not conflict (null != null in SQL)."""

    def test_two_null_emails_do_not_conflict(self, db):
        User.objects.create_user(username="a", password="x", email=None)
        User.objects.create_user(username="b", password="x", email=None)  # must not raise

    def test_two_identical_emails_raise(self, db):
        User.objects.create_user(username="a", password="x", email="dup@test.com")
        with pytest.raises(Exception):  # IntegrityError wrapped by Django ORM
            User.objects.create_user(username="b", password="x", email="dup@test.com")


# ---------------------------------------------------------------------------
# User.actor_url / actor_inbox / actor_outbox
# ---------------------------------------------------------------------------


class TestUserActorURLs:
    """AP URL properties for local and remote users."""

    def test_local_actor_url(self, user, settings):
        settings.AP_BASE_URL = "https://test.social"
        assert user.actor_url == "https://test.social/users/testuser"

    def test_local_actor_inbox(self, user, settings):
        settings.AP_BASE_URL = "https://test.social"
        assert user.actor_inbox == "https://test.social/users/testuser/inbox"

    def test_local_actor_outbox(self, user, settings):
        settings.AP_BASE_URL = "https://test.social"
        assert user.actor_outbox == "https://test.social/users/testuser/outbox"

    def test_remote_actor_url_returns_ap_id(self, db):
        remote = User.objects.create_user(
            username="remote",
            password="x",
            remote=True,
            ap_id="https://remote.social/users/alice",
        )
        assert remote.actor_url == "https://remote.social/users/alice"

    def test_remote_actor_url_returns_none_when_ap_id_missing(self, db):
        remote = User.objects.create_user(username="remote2", password="x", remote=True)
        assert remote.actor_url is None

    def test_remote_actor_inbox_returns_none_when_inbox_url_missing(self, db):
        remote = User.objects.create_user(username="remote3", password="x", remote=True)
        assert remote.actor_inbox is None

    def test_remote_actor_outbox_returns_none_when_outbox_url_missing(self, db):
        remote = User.objects.create_user(username="remote4", password="x", remote=True)
        assert remote.actor_outbox is None

    def test_remote_actor_inbox_returns_inbox_url_when_set(self, db):
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
    def test_returns_at_prefixed_path(self, user):
        url = user.get_absolute_url()
        assert url == f"/@{user.username}/"


# ---------------------------------------------------------------------------
# User language preference defaults
# ---------------------------------------------------------------------------


class TestUserLanguageDefaults:
    def test_content_language_defaults_to_fr(self, db):
        u = User.objects.create_user(username="lang", password="x")
        assert u.content_language == "fr"

    def test_preferred_languages_defaults_to_empty_list(self, db):
        u = User.objects.create_user(username="lang2", password="x")
        assert u.preferred_languages == []


# ---------------------------------------------------------------------------
# ProfileView
# ---------------------------------------------------------------------------


class TestProfileView:
    """GET /@<username>/ — public profile page."""

    def test_active_user_is_found(self, client, user):
        """Active user exists in queryset — view proceeds past 404 check."""
        client.raise_request_exception = False
        response = client.get(f"/@{user.username}/")
        assert response.status_code != 404

    def test_inactive_user_returns_404(self, client, db):
        """is_active=False users are excluded from queryset."""
        client.raise_request_exception = False
        inactive = User.objects.create_user(
            username="inactive", password="x", is_active=False
        )
        response = client.get(f"/@{inactive.username}/")
        assert response.status_code == 404

    def test_nonexistent_username_returns_404(self, client, db):
        client.raise_request_exception = False
        response = client.get("/@nobody_at_all/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# ProfileEditView
# ---------------------------------------------------------------------------


class TestProfileEditView:
    """GET/POST /@<username>/edit/ — authenticated profile editor."""

    def test_anonymous_redirects_to_login(self, client, user):
        response = client.get(f"/@{user.username}/edit/")
        assert response.status_code == 302
        assert "/accounts/" in response["Location"]

    def test_username_mismatch_redirects_to_own_edit_url(self, client, user, other_user):
        """Visiting @other/edit/ while logged in as self → redirected to own edit URL."""
        client.force_login(user)
        response = client.get(f"/@{other_user.username}/edit/")
        assert response.status_code == 302
        assert user.username in response["Location"]
        assert other_user.username not in response["Location"]

    def test_correct_username_passes_dispatch(self, client, user):
        """Authenticated user on their own URL bypasses redirect logic."""
        client.raise_request_exception = False
        client.force_login(user)
        response = client.get(f"/@{user.username}/edit/")
        # Not a login redirect — dispatch reached the view
        location = response.get("Location", "")
        assert "/accounts/" not in location


# ---------------------------------------------------------------------------
# ProfileForm
# ---------------------------------------------------------------------------


class TestProfileForm:
    """ProfileForm.clean_preferred_languages contract."""

    def test_empty_preferred_languages_returns_empty_list(self, db, user):
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

    def test_valid_list_passes_through_unchanged(self, db, user):
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
