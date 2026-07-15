"""Tests for the Muses settings tab (activation switch + credit counter)."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.users.models import User

pytestmark = pytest.mark.django_db

URL = reverse("users:settings_muses")


def test_tab_shows_credits_and_switch(client: Client, user: User) -> None:
    user.muses_credits = 42
    user.save(update_fields=["muses_credits"])
    client.force_login(user)

    resp = client.get(URL)

    assert resp.status_code == 200
    body = resp.content.decode()
    assert "42" in body
    assert "muses_enabled" in body  # the activation switch field


def test_switch_toggles_activation(client: Client, user: User) -> None:
    assert user.muses_enabled is False
    client.force_login(user)

    resp = client.post(URL, {"muses_enabled": "on", "muses_post_ingest_optin": "on"})

    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.muses_enabled is True
    assert user.muses_post_ingest_optin is True


def test_switch_off_clears_activation(client: Client, user: User) -> None:
    user.muses_enabled = True
    user.save(update_fields=["muses_enabled"])
    client.force_login(user)

    resp = client.post(URL, {})  # unchecked switches submit nothing

    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.muses_enabled is False


def test_requires_login(client: Client) -> None:
    resp = client.get(URL)
    assert resp.status_code == 302
    assert "/accounts/login" in resp.url or "login" in resp.url
