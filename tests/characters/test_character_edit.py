"""Tests for characters:edit (character_form.html, Phase 4 task 9).

character_form.html is edit-only: no route ever calls it with character=None,
so the template's dead "New character"/create branch was removed. These tests
guard against that regression and exercise the existing character_edit view
(no prior test coverage existed for this view).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import Character
from suddenly.users.models import User


@pytest.fixture
def plain_static(settings: Any) -> None:
    """Swap the manifest static storage for the plain one (no frontend build in tests)."""
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def logged_client(client: Client, user: User) -> Client:
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestCharacterFormEditOnly:
    def test_get_renders_edit_mode_only(
        self, plain_static: None, logged_client: Client, character: Character
    ) -> None:
        # Default LANGUAGE_CODE is "fr" (no Accept-Language header sent by the
        # test client) -- "Edit character"/"New character" have French catalog
        # entries, so the rendered page carries the translated strings.
        url = reverse("characters:edit", kwargs={"slug": character.slug})
        resp = logged_client.get(url)
        content = resp.content.decode()

        assert resp.status_code == 200
        assert "Modifier le personnage" in content
        assert "Nouveau personnage" not in content
        # No create-mode fallback link to the list left in the markup — the
        # exact-quoted href avoids false positives from unrelated nav links
        # that also start with "/characters/" (e.g. the dashboard link).
        list_url = reverse("characters:list")
        assert f'href="{list_url}"' not in content
        assert reverse("characters:detail", kwargs={"slug": character.slug}) in content

    def test_stranger_forbidden(
        self, client: Client, other_user: User, character: Character
    ) -> None:
        client.force_login(other_user)
        url = reverse("characters:edit", kwargs={"slug": character.slug})
        resp = client.get(url)
        assert resp.status_code == 404  # get_object_or_404 scopes to creator=request.user

    def test_valid_post_updates_and_redirects(
        self, plain_static: None, logged_client: Client, character: Character
    ) -> None:
        url = reverse("characters:edit", kwargs={"slug": character.slug})
        resp = logged_client.post(
            url,
            {
                "name": "Nouveau nom",
                "description": "Nouvelle description",
                "sheet_url": "https://example.com/feuille",
                "tags": "",
            },
        )
        character.refresh_from_db()

        assert resp.status_code == 302
        assert resp["Location"] == reverse("characters:detail", kwargs={"slug": character.slug})
        assert character.name == "Nouveau nom"
        assert character.description == "Nouvelle description"

    def test_empty_name_re_renders_edit_mode_with_422_like_error(
        self, plain_static: None, logged_client: Client, character: Character
    ) -> None:
        url = reverse("characters:edit", kwargs={"slug": character.slug})
        resp = logged_client.post(url, {"name": "   "})
        content = resp.content.decode()

        assert resp.status_code == 200  # character_edit re-renders 200, not 422 (own convention)
        assert "Le nom est obligatoire." in content
        assert "Modifier le personnage" in content
        assert "Nouveau personnage" not in content
