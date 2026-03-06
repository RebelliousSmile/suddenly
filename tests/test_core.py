"""
Tests for suddenly.core.mixins and suddenly.core.utils.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from suddenly.core.mixins import ActivityPubMixin
from suddenly.core.utils import generate_unique_slug

# ---------------------------------------------------------------------------
# ActivityPubMixin tests
# ---------------------------------------------------------------------------


class TestActivityPubMixinGetApId:
    """Tests for ActivityPubMixin.get_ap_id()."""

    def test_returns_stored_ap_id_when_set(self) -> None:
        """get_ap_id returns the stored ap_id if one exists."""
        instance = ActivityPubMixin.__new__(ActivityPubMixin)
        instance.ap_id = "https://remote.example/actors/42"
        assert instance.get_ap_id() == "https://remote.example/actors/42"

    def test_generates_http_url_when_debug_true(self, settings: object) -> None:
        """get_ap_id uses http:// when DEBUG is True."""
        settings.DEBUG = True  # type: ignore[attr-defined]
        settings.DOMAIN = "test.social"  # type: ignore[attr-defined]

        instance = ActivityPubMixin.__new__(ActivityPubMixin)
        instance.ap_id = ""
        instance.get_absolute_url = lambda: "/users/alice"  # type: ignore[assignment]

        assert instance.get_ap_id() == "http://test.social/users/alice"

    def test_generates_https_url_when_debug_false(self, settings: object) -> None:
        """get_ap_id uses https:// when DEBUG is False."""
        settings.DEBUG = False  # type: ignore[attr-defined]
        settings.DOMAIN = "test.social"  # type: ignore[attr-defined]

        instance = ActivityPubMixin.__new__(ActivityPubMixin)
        instance.ap_id = ""
        instance.get_absolute_url = lambda: "/users/alice"  # type: ignore[assignment]

        assert instance.get_ap_id() == "https://test.social/users/alice"

    def test_generates_url_when_ap_id_is_none(self, settings: object) -> None:
        """get_ap_id generates a URL when ap_id is None (falsy)."""
        settings.DEBUG = True  # type: ignore[attr-defined]
        settings.DOMAIN = "test.social"  # type: ignore[attr-defined]

        instance = ActivityPubMixin.__new__(ActivityPubMixin)
        instance.ap_id = None
        instance.get_absolute_url = lambda: "/games/123"  # type: ignore[assignment]

        assert instance.get_ap_id() == "http://test.social/games/123"


class TestActivityPubMixinIsRemote:
    """Tests for ActivityPubMixin.is_remote()."""

    def test_local_instance_is_not_remote(self) -> None:
        """is_remote returns False for local entities."""
        instance = ActivityPubMixin.__new__(ActivityPubMixin)
        instance.local = True
        assert instance.is_remote() is False

    def test_remote_instance_is_remote(self) -> None:
        """is_remote returns True for remote entities."""
        instance = ActivityPubMixin.__new__(ActivityPubMixin)
        instance.local = False
        assert instance.is_remote() is True


# ---------------------------------------------------------------------------
# generate_unique_slug tests
# ---------------------------------------------------------------------------


class TestGenerateUniqueSlug:
    """Tests for generate_unique_slug()."""

    def test_basic_slug_generation(self) -> None:
        """Generates a slug from a plain string when no collision exists."""
        mock_manager = MagicMock()
        mock_qs = MagicMock()
        mock_manager.all.return_value = mock_qs
        mock_qs.filter.return_value.exists.return_value = False

        model_class = MagicMock()
        model_class._default_manager = mock_manager

        result = generate_unique_slug(model_class, "My Great Title")
        assert result == "my-great-title"
        mock_qs.filter.assert_called_once_with(slug="my-great-title")

    def test_slug_collision_appends_counter(self) -> None:
        """Appends -1, -2, etc. when the base slug already exists."""
        mock_manager = MagicMock()
        mock_qs = MagicMock()
        mock_manager.all.return_value = mock_qs

        # First call (base slug) collides, second call (-1) is free
        mock_qs.filter.return_value.exists.side_effect = [True, False]

        model_class = MagicMock()
        model_class._default_manager = mock_manager

        result = generate_unique_slug(model_class, "Duplicate Title")
        assert result == "duplicate-title-1"

    def test_multiple_collisions(self) -> None:
        """Increments counter until a free slug is found."""
        mock_manager = MagicMock()
        mock_qs = MagicMock()
        mock_manager.all.return_value = mock_qs

        # base, -1, -2 collide; -3 is free
        mock_qs.filter.return_value.exists.side_effect = [True, True, True, False]

        model_class = MagicMock()
        model_class._default_manager = mock_manager

        result = generate_unique_slug(model_class, "Popular")
        assert result == "popular-3"

    def test_existing_instance_excluded_from_queryset(self) -> None:
        """When updating, the current instance is excluded from collision check."""
        mock_manager = MagicMock()
        mock_qs = MagicMock()
        mock_excluded_qs = MagicMock()
        mock_manager.all.return_value = mock_qs
        mock_qs.exclude.return_value = mock_excluded_qs
        mock_excluded_qs.filter.return_value.exists.return_value = False

        model_class = MagicMock()
        model_class._default_manager = mock_manager

        instance = MagicMock()
        instance.pk = "existing-pk-123"

        result = generate_unique_slug(model_class, "Updated Title", instance=instance)
        assert result == "updated-title"
        mock_qs.exclude.assert_called_once_with(pk="existing-pk-123")
        mock_excluded_qs.filter.assert_called_once_with(slug="updated-title")

    def test_instance_without_pk_not_excluded(self) -> None:
        """An unsaved instance (pk=None) does not trigger exclude."""
        mock_manager = MagicMock()
        mock_qs = MagicMock()
        mock_manager.all.return_value = mock_qs
        mock_qs.filter.return_value.exists.return_value = False

        model_class = MagicMock()
        model_class._default_manager = mock_manager

        instance = MagicMock()
        instance.pk = None

        result = generate_unique_slug(model_class, "New Entry", instance=instance)
        assert result == "new-entry"
        mock_qs.exclude.assert_not_called()
