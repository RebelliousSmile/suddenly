"""Tests for the character hover-card endpoint (maquette §10 Tooltip PNJ)."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import CharacterStatus
from tests.factories import CharacterFactory, UserFactory


@pytest.mark.django_db
def test_card_renders_without_session(client: Client) -> None:
    character = CharacterFactory(name="Sable-Gris")
    resp = client.get(reverse("characters:card", kwargs={"slug": character.slug}))
    assert resp.status_code == 200
    assert b"Sable-Gris" in resp.content


@pytest.mark.django_db
def test_card_available_npc_offers_link_actions(client: Client) -> None:
    """An available NPC (unowned) shows Claim / Adopt / Fork."""
    npc = CharacterFactory(status=CharacterStatus.NPC, owner=None)
    resp = client.get(reverse("characters:card", kwargs={"slug": npc.slug}))
    body = resp.content
    for link_type in ("claim", "adopt", "fork"):
        assert (
            reverse(
                "characters:link_request_form",
                kwargs={"slug": npc.slug, "link_type": link_type},
            ).encode()
            in body
        )


@pytest.mark.django_db
def test_card_owned_pc_hides_link_actions(client: Client) -> None:
    owner = UserFactory()
    pc = CharacterFactory(status=CharacterStatus.PC, owner=owner)
    resp = client.get(reverse("characters:card", kwargs={"slug": pc.slug}))
    # No claim affordance on a character that is not available.
    assert (
        reverse(
            "characters:link_request_form", kwargs={"slug": pc.slug, "link_type": "claim"}
        ).encode()
        not in resp.content
    )
    # But the "Fiche" link to the detail page is always there.
    assert reverse("characters:detail", kwargs={"slug": pc.slug}).encode() in resp.content
