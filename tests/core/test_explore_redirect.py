"""Tests for the deprecated Explorer redirect to Stories (SUD-V5)."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_explore_redirects_to_stories(client: Client) -> None:
    response = client.get(reverse("feed:explore"))
    assert response.status_code == 301
    assert response["Location"] == reverse("games:stories")
