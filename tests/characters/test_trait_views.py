"""Tests for the traits editor views (issue B) and sheet display (issue C)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import Action, Character, Trait, TraitSet
from suddenly.users.models import User


@pytest.fixture
def plain_static(settings: Any) -> None:
    """Swap the manifest static storage for the plain one.

    Full-page templates extend base.html, which resolves hashed static assets
    via the manifest storage — absent in tests (no frontend build). The plain
    backend returns unhashed URLs so full-page renders work without collectstatic.
    """
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def logged_client(client: Client, user: User) -> Client:
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestTraitsEditorAccess:
    def test_owner_can_open_editor(
        self, plain_static: None, logged_client: Client, character: Character
    ) -> None:
        url = reverse("characters:traits_editor", kwargs={"slug": character.slug})
        resp = logged_client.get(url)
        assert resp.status_code == 200
        assert b"Traits" in resp.content

    def test_stranger_is_forbidden(
        self, client: Client, other_user: User, character: Character
    ) -> None:
        client.force_login(other_user)
        url = reverse("characters:traits_editor", kwargs={"slug": character.slug})
        resp = client.get(url)
        assert resp.status_code == 403

    def test_anonymous_redirected_to_login(self, client: Client, character: Character) -> None:
        url = reverse("characters:traits_editor", kwargs={"slug": character.slug})
        resp = client.get(url)
        assert resp.status_code == 302


@pytest.mark.django_db
class TestTraitSetCrud:
    def test_create_set(self, logged_client: Client, character: Character) -> None:
        url = reverse("characters:trait_set_create", kwargs={"slug": character.slug})
        resp = logged_client.post(url, {"label": "Aspects", "order": 0})
        assert resp.status_code == 200
        assert character.trait_sets.filter(label="Aspects").exists()

    def test_delete_set_cascades(self, logged_client: Client, character: Character) -> None:
        ts = TraitSet.objects.create(character=character, label="X")
        Trait.objects.create(trait_set=ts, name="t")
        url = reverse(
            "characters:trait_set_delete",
            kwargs={"slug": character.slug, "set_pk": ts.pk},
        )
        resp = logged_client.post(url)
        assert resp.status_code == 200
        assert not TraitSet.objects.filter(pk=ts.pk).exists()
        assert Trait.objects.count() == 0

    def test_stranger_cannot_create_set(
        self, client: Client, other_user: User, character: Character
    ) -> None:
        client.force_login(other_user)
        url = reverse("characters:trait_set_create", kwargs={"slug": character.slug})
        resp = client.post(url, {"label": "Sneaky"})
        assert resp.status_code == 403
        assert not character.trait_sets.exists()


@pytest.mark.django_db
class TestTraitCrud:
    def test_create_trait_with_value(self, logged_client: Client, character: Character) -> None:
        ts = TraitSet.objects.create(character=character)
        url = reverse(
            "characters:trait_create",
            kwargs={"slug": character.slug, "set_pk": ts.pk},
        )
        resp = logged_client.post(url, {"name": "Casse-cou", "value": "3"})
        assert resp.status_code == 200
        trait = ts.traits.get(name="Casse-cou")
        assert trait.value == 3
        assert b"+3" in resp.content

    def test_create_valueless_trait(self, logged_client: Client, character: Character) -> None:
        """Empty value posts as a valueless tag (None), never rejected."""
        ts = TraitSet.objects.create(character=character)
        url = reverse(
            "characters:trait_create",
            kwargs={"slug": character.slug, "set_pk": ts.pk},
        )
        resp = logged_client.post(url, {"name": "Sworn", "value": ""})
        assert resp.status_code == 200
        assert ts.traits.get(name="Sworn").value is None

    def test_out_of_range_value_accepted(self, logged_client: Client, character: Character) -> None:
        """No server-side range validation: overflow beyond ±5 persists."""
        ts = TraitSet.objects.create(character=character)
        url = reverse(
            "characters:trait_create",
            kwargs={"slug": character.slug, "set_pk": ts.pk},
        )
        resp = logged_client.post(url, {"name": "Épique", "value": "99"})
        assert resp.status_code == 200
        assert ts.traits.get(name="Épique").value == 99

    def test_delete_trait(self, logged_client: Client, character: Character) -> None:
        ts = TraitSet.objects.create(character=character)
        trait = Trait.objects.create(trait_set=ts, name="Gone")
        url = reverse(
            "characters:trait_delete",
            kwargs={"slug": character.slug, "trait_pk": trait.pk},
        )
        resp = logged_client.post(url)
        assert resp.status_code == 200
        assert not Trait.objects.filter(pk=trait.pk).exists()


@pytest.mark.django_db
class TestActionCrud:
    def test_create_multi_trait_action(self, logged_client: Client, character: Character) -> None:
        ts = TraitSet.objects.create(character=character)
        a = Trait.objects.create(trait_set=ts, name="A", value=1)
        b = Trait.objects.create(trait_set=ts, name="B")
        url = reverse(
            "characters:action_create",
            kwargs={"slug": character.slug, "set_pk": ts.pk},
        )
        resp = logged_client.post(
            url,
            {
                "name": "Combo",
                "traits": [str(a.pk), str(b.pk)],
                "condition": "Quand X",
                "outcome": "Alors Y",
            },
        )
        assert resp.status_code == 200
        action = ts.actions.get(name="Combo")
        assert action.traits.count() == 2
        assert action.condition == "Quand X"
        assert action.outcome == "Alors Y"

    def test_delete_action(self, logged_client: Client, character: Character) -> None:
        ts = TraitSet.objects.create(character=character)
        action = Action.objects.create(trait_set=ts, name="Gone")
        url = reverse(
            "characters:action_delete",
            kwargs={"slug": character.slug, "action_pk": action.pk},
        )
        resp = logged_client.post(url)
        assert resp.status_code == 200
        assert not Action.objects.filter(pk=action.pk).exists()


@pytest.mark.django_db
class TestSheetDisplay:
    def test_traits_render_on_public_sheet(
        self, plain_static: None, client: Client, character: Character
    ) -> None:
        ts = TraitSet.objects.create(character=character, label="Aspects")
        Trait.objects.create(trait_set=ts, name="Casse-cou", value=3)
        Trait.objects.create(trait_set=ts, name="Sworn")  # valueless
        action = Action.objects.create(
            trait_set=ts, name="Foncer", condition="Quand tu fonces", outcome="Tu t'exposes"
        )
        action.traits.set(list(ts.traits.all()))

        url = reverse("characters:detail", kwargs={"slug": character.slug})
        resp = client.get(url)
        content = resp.content.decode()
        assert resp.status_code == 200
        assert "Aspects" in content
        assert "Casse-cou" in content
        assert "+3" in content
        assert "Sworn" in content
        assert "Foncer" in content
        assert "Quand tu fonces" in content
        # No evaluation affordance leaks into the sheet.
        for forbidden in ("Lancer", "Résoudre", "Calculer", "Roll", "Resolve"):
            assert forbidden not in content

    def test_sheet_url_block_shown(
        self, plain_static: None, client: Client, character: Character
    ) -> None:
        character.sheet_url = "https://example.com/sheet"
        character.save(update_fields=["sheet_url"])
        url = reverse("characters:detail", kwargs={"slug": character.slug})
        resp = client.get(url)
        assert b"https://example.com/sheet" in resp.content

    def test_edit_link_only_for_maintainer(
        self, plain_static: None, client: Client, user: User, other_user: User, character: Character
    ) -> None:
        editor_url = reverse("characters:traits_editor", kwargs={"slug": character.slug})
        detail_url = reverse("characters:detail", kwargs={"slug": character.slug})

        client.force_login(user)
        assert editor_url.encode() in client.get(detail_url).content

        client.force_login(other_user)
        assert editor_url.encode() not in client.get(detail_url).content
