from __future__ import annotations

import pytest
from django.test import Client

from suddenly.docs import nav


@pytest.fixture
def client() -> Client:
    return Client()


def test_index_200(client: Client) -> None:
    response = client.get("/docs/")
    assert response.status_code == 200
    assert b"Documentation" in response.content


def test_page_doc_index_200(client: Client) -> None:
    response = client.get("/docs/doc/index/")
    assert response.status_code == 200
    assert b"Suddenly" in response.content


def test_page_projet_architecture_200(client: Client) -> None:
    response = client.get("/docs/projet/architecture/")
    assert response.status_code == 200


def test_page_wireframes_report_links_200(client: Client) -> None:
    response = client.get("/docs/wireframes/report-links/")
    assert response.status_code == 200


def test_page_404_unknown_section(client: Client) -> None:
    response = client.get("/docs/inexistant/foo/")
    assert response.status_code == 404


def test_page_404_unknown_slug(client: Client) -> None:
    response = client.get("/docs/doc/inexistant/")
    assert response.status_code == 404


def test_nav_resolve_valid() -> None:
    path = nav.resolve("doc", "index")
    assert path is not None
    assert path.exists()


def test_nav_resolve_invalid() -> None:
    assert nav.resolve("doc", "nope") is None
