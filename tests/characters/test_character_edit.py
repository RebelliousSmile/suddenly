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
from suddenly.core.models import Tag
from suddenly.games.models import Rapport, RapportKind, Report, ReportStatus
from suddenly.users.models import User
from tests.factories import GameFactory


def _give_character_a_post(character: Character) -> None:
    """Make the character the actor of one post (Rapport) → locks its game (#154)."""
    report = Report.objects.create(
        game=character.origin_game,
        author=character.creator,
        content="Scene body.",
        status=ReportStatus.DRAFT,
    )
    Rapport.objects.create(
        report=report, kind=RapportKind.ACTION, content="It acts.", actor=character
    )


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

    def test_edit_persists_background_and_secrets(
        self, plain_static: None, logged_client: Client, character: Character
    ) -> None:
        url = reverse("characters:edit", kwargs={"slug": character.slug})
        resp = logged_client.post(
            url,
            {
                "name": character.name,
                "description": "",
                "background": "Né dans la tempête.",
                "secrets": "Travaille pour l'ennemi.",
                "tags": "",
            },
        )
        character.refresh_from_db()

        assert resp.status_code == 302
        assert character.background == "Né dans la tempête."
        assert character.secrets == "Travaille pour l'ennemi."

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


@pytest.mark.django_db
class TestCharacterGameEdit:
    """#154 — the character's game (origin_game) is editable, locked once it has posts."""

    def test_unlocked_get_shows_game_select(
        self, plain_static: None, logged_client: Client, user: User, character: Character
    ) -> None:
        other = GameFactory(owner=user)
        content = logged_client.get(
            reverse("characters:edit", kwargs={"slug": character.slug})
        ).content.decode()
        # Editable select present (structural, language-independent) + both owned games.
        assert 'name="origin_game"' in content
        assert other.title in content
        assert character.origin_game.title in content

    def test_change_game_persists_and_redirects(
        self, plain_static: None, logged_client: Client, user: User, character: Character
    ) -> None:
        other = GameFactory(owner=user)
        resp = logged_client.post(
            reverse("characters:edit", kwargs={"slug": character.slug}),
            {"name": character.name, "origin_game": str(other.pk), "tags": ""},
        )
        character.refresh_from_db()
        assert resp.status_code == 302
        assert character.origin_game_id == other.pk

    def test_change_appears_in_new_game_roster(
        self, plain_static: None, logged_client: Client, user: User, character: Character
    ) -> None:
        other = GameFactory(owner=user)
        logged_client.post(
            reverse("characters:edit", kwargs={"slug": character.slug}),
            {"name": character.name, "origin_game": str(other.pk), "tags": ""},
        )
        # (B) The character now surfaces in the new game's roster (game_detail).
        body = logged_client.get(
            reverse("games:detail", kwargs={"pk": str(other.pk)})
        ).content.decode()
        assert character.name in body

    def test_unowned_game_rejected(
        self,
        plain_static: None,
        logged_client: Client,
        character: Character,
        other_user: User,
    ) -> None:
        foreign = GameFactory(owner=other_user)
        original_game_id = character.origin_game_id
        resp = logged_client.post(
            reverse("characters:edit", kwargs={"slug": character.slug}),
            {"name": character.name, "origin_game": str(foreign.pk), "tags": ""},
        )
        character.refresh_from_db()
        assert resp.status_code == 200  # re-render with error (edit convention)
        assert character.origin_game_id == original_game_id

    def test_locked_get_has_no_editable_select(
        self, plain_static: None, logged_client: Client, character: Character
    ) -> None:
        _give_character_a_post(character)
        content = logged_client.get(
            reverse("characters:edit", kwargs={"slug": character.slug})
        ).content.decode()
        # Locked → a disabled field, not a submittable select.
        assert 'name="origin_game"' not in content
        assert 'id="origin_game"' in content
        assert "disabled" in content

    def test_locked_post_ignores_game_change(
        self, plain_static: None, logged_client: Client, user: User, character: Character
    ) -> None:
        _give_character_a_post(character)
        other = GameFactory(owner=user)
        original_game_id = character.origin_game_id
        resp = logged_client.post(
            reverse("characters:edit", kwargs={"slug": character.slug}),
            {"name": "Renommé", "origin_game": str(other.pk), "tags": ""},
        )
        character.refresh_from_db()
        # Server guard: forged origin_game ignored; other fields still saved.
        assert resp.status_code == 302
        assert character.origin_game_id == original_game_id
        assert character.name == "Renommé"


@pytest.mark.django_db
class TestSheetExtraFields:
    """#148 — tags + background (public) + secrets (maintainer-only) on the sheet."""

    def _prepare(self, character: Character) -> None:
        character.background = "PUBLIC-BACKSTORY-XYZ"
        character.secrets = "HIDDEN-SECRET-XYZ"
        character.save(update_fields=["background", "secrets"])
        character.tags.set(Tag.resolve_names("héros"))

    def test_tags_and_background_shown_publicly(
        self, plain_static: None, client: Client, character: Character
    ) -> None:
        self._prepare(character)
        content = client.get(
            reverse("characters:detail", kwargs={"slug": character.slug})
        ).content.decode()
        assert "héros" in content
        assert "PUBLIC-BACKSTORY-XYZ" in content

    def test_secrets_visible_to_maintainer(
        self, plain_static: None, logged_client: Client, character: Character
    ) -> None:
        # `character` is created by `user`; `logged_client` is logged in as `user`.
        self._prepare(character)
        content = logged_client.get(
            reverse("characters:detail", kwargs={"slug": character.slug})
        ).content.decode()
        assert "HIDDEN-SECRET-XYZ" in content

    def test_secrets_hidden_from_others(
        self, plain_static: None, client: Client, other_user: User, character: Character
    ) -> None:
        self._prepare(character)
        client.force_login(other_user)
        content = client.get(
            reverse("characters:detail", kwargs={"slug": character.slug})
        ).content.decode()
        assert "HIDDEN-SECRET-XYZ" not in content
        # ...but the public background still shows.
        assert "PUBLIC-BACKSTORY-XYZ" in content

    def test_secrets_hidden_from_anonymous(
        self, plain_static: None, client: Client, character: Character
    ) -> None:
        self._prepare(character)
        content = client.get(
            reverse("characters:detail", kwargs={"slug": character.slug})
        ).content.decode()
        assert "HIDDEN-SECRET-XYZ" not in content
