"""Tests for the citation promotion axis (prompt: remontée des citations).

Covers the double lock (QuoteQuerySet.promotable), the expires_at<->EPHEMERAL
constraint, and that no non-promotable citation reaches a public surface
(vitrine, /citations, story, character).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from suddenly.characters.models import Quote, QuoteVisibility
from suddenly.games.models import ReportStatus, ReportVisibility
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory


def _released_report(**kwargs: object):
    return ReportFactory(
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=timezone.now(),
        **kwargs,
    )


def _unreleased_report(**kwargs: object):
    return ReportFactory(
        status=ReportStatus.PUBLISHED,
        visibility=ReportVisibility.PUBLIC,
        published_at=timezone.now(),
        released_at=None,
        **kwargs,
    )


def _quote(report, *, visibility=QuoteVisibility.PUBLIC, expires_at=None, text="A line."):
    return Quote.objects.create(
        report=report,
        character=CharacterFactory(),
        author=report.author,
        content=text,
        visibility=visibility,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# promotable() — the double lock
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_promotable_includes_public_released_not_expired() -> None:
    q = _quote(_released_report(), visibility=QuoteVisibility.PUBLIC)
    assert q in Quote.objects.promotable()


@pytest.mark.django_db
def test_promotable_excludes_public_on_unreleased_report() -> None:
    """Wall closed → even a public quote does not rise."""
    q = _quote(_unreleased_report(), visibility=QuoteVisibility.PUBLIC)
    assert q not in Quote.objects.promotable()


@pytest.mark.django_db
def test_promotable_excludes_private_on_released_report() -> None:
    """Report released but the author kept the quote private → it does not rise."""
    q = _quote(_released_report(), visibility=QuoteVisibility.PRIVATE)
    assert q not in Quote.objects.promotable()


@pytest.mark.django_db
def test_promotable_excludes_expired_ephemeral() -> None:
    q = _quote(
        _released_report(),
        visibility=QuoteVisibility.EPHEMERAL,
        expires_at=timezone.now() - timedelta(hours=1),
    )
    assert q not in Quote.objects.promotable()


@pytest.mark.django_db
def test_promotable_excludes_quote_without_report() -> None:
    """A quote with no source report can never cross the wall."""
    q = Quote.objects.create(
        character=CharacterFactory(),
        author=UserFactory(),
        content="Orphan",
        visibility=QuoteVisibility.PUBLIC,
    )
    assert q not in Quote.objects.promotable()


# ---------------------------------------------------------------------------
# CheckConstraint: expires_at set iff EPHEMERAL
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_constraint_public_with_expiry_fails() -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _quote(
                _released_report(),
                visibility=QuoteVisibility.PUBLIC,
                expires_at=timezone.now() + timedelta(days=1),
            )


@pytest.mark.django_db
def test_constraint_ephemeral_without_expiry_fails() -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _quote(_released_report(), visibility=QuoteVisibility.EPHEMERAL, expires_at=None)


@pytest.mark.django_db
def test_constraint_ephemeral_with_expiry_ok() -> None:
    q = _quote(
        _released_report(),
        visibility=QuoteVisibility.EPHEMERAL,
        expires_at=timezone.now() + timedelta(days=1),
    )
    assert q.pk is not None


# ---------------------------------------------------------------------------
# Public surfaces
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_citations_wall_200_without_session(client: Client) -> None:
    resp = client.get(reverse("core:quotes"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_citations_wall_shows_only_promotable(client: Client) -> None:
    good = _quote(_released_report(), text="PROMOTABLE-LINE")
    hidden = _quote(_unreleased_report(), text="WALLED-LINE")
    _quote(_released_report(), visibility=QuoteVisibility.PRIVATE, text="PRIVATE-LINE")

    resp = client.get(reverse("core:quotes"))
    assert good.content.encode() in resp.content
    assert hidden.content.encode() not in resp.content
    assert b"PRIVATE-LINE" not in resp.content


@pytest.mark.django_db
def test_vitrine_anonymous_exposes_no_non_promotable(client: Client) -> None:
    _quote(_unreleased_report(), text="WALLED-VITRINE")
    _quote(_released_report(), visibility=QuoteVisibility.PRIVATE, text="PRIVATE-VITRINE")
    promotable = _quote(_released_report(), text="PROMOTABLE-VITRINE")

    resp = client.get(reverse("core:home"))
    assert resp.status_code == 200
    assert promotable.content.encode() in resp.content
    assert b"WALLED-VITRINE" not in resp.content
    assert b"PRIVATE-VITRINE" not in resp.content


@pytest.mark.django_db
def test_character_page_shows_only_promotable(client: Client) -> None:
    character = CharacterFactory()
    released = _released_report()
    unreleased = _unreleased_report()
    Quote.objects.create(
        report=released,
        character=character,
        author=released.author,
        content="CHAR-PROMOTABLE",
        visibility=QuoteVisibility.PUBLIC,
    )
    Quote.objects.create(
        report=unreleased,
        character=character,
        author=unreleased.author,
        content="CHAR-WALLED",
        visibility=QuoteVisibility.PUBLIC,
    )

    resp = client.get(reverse("characters:detail", kwargs={"slug": character.slug}))
    assert resp.status_code == 200
    assert b"CHAR-PROMOTABLE" in resp.content
    assert b"CHAR-WALLED" not in resp.content


@pytest.mark.django_db
def test_story_page_lists_only_promotable(client: Client) -> None:
    game = GameFactory()
    released = _released_report(game=game)
    Quote.objects.create(
        report=released,
        character=CharacterFactory(),
        author=released.author,
        content="STORY-PROMOTABLE",
        visibility=QuoteVisibility.PUBLIC,
    )
    # Private one on the same released report must not appear.
    Quote.objects.create(
        report=released,
        character=CharacterFactory(),
        author=released.author,
        content="STORY-PRIVATE",
        visibility=QuoteVisibility.PRIVATE,
    )

    resp = client.get(reverse("games:story_detail", kwargs={"pk": game.pk}))
    assert resp.status_code == 200
    assert b"STORY-PROMOTABLE" in resp.content
    assert b"STORY-PRIVATE" not in resp.content


# ---------------------------------------------------------------------------
# §5 — author marks / manages a citation on their report
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_quote_create_by_author(client: Client) -> None:
    author = UserFactory()
    game = GameFactory(owner=author)
    report = _released_report(game=game, author=author)
    character = CharacterFactory(origin_game=game)

    client.force_login(author)
    url = reverse("games:quote_create", kwargs={"game_pk": game.pk, "pk": report.pk})
    resp = client.post(
        url, {"content": "Marked line.", "character": character.slug, "visibility": "public"}
    )

    assert resp.status_code == 200
    quote = Quote.objects.get(report=report)
    assert quote.content == "Marked line."
    assert quote.visibility == QuoteVisibility.PUBLIC


@pytest.mark.django_db
def test_quote_create_non_author_forbidden(client: Client) -> None:
    author = UserFactory()
    intruder = UserFactory()
    report = _released_report(author=author)
    character = CharacterFactory()

    client.force_login(intruder)
    url = reverse("games:quote_create", kwargs={"game_pk": report.game.pk, "pk": report.pk})
    resp = client.post(url, {"content": "Nope.", "character": character.slug})

    assert resp.status_code == 403
    assert not Quote.objects.filter(report=report).exists()


@pytest.mark.django_db
def test_quote_create_on_unreleased_report_waits(client: Client) -> None:
    """A quote may be created on an unreleased report; it just isn't promotable."""
    author = UserFactory()
    report = _unreleased_report(author=author)
    character = CharacterFactory()

    client.force_login(author)
    url = reverse("games:quote_create", kwargs={"game_pk": report.game.pk, "pk": report.pk})
    resp = client.post(
        url, {"content": "Held.", "character": character.slug, "visibility": "public"}
    )

    assert resp.status_code == 200
    quote = Quote.objects.get(report=report)
    assert quote not in Quote.objects.promotable()


@pytest.mark.django_db
def test_quote_delete_by_author(client: Client) -> None:
    author = UserFactory()
    report = _released_report(author=author)
    quote = _quote(report)

    client.force_login(author)
    url = reverse(
        "games:quote_delete",
        kwargs={"game_pk": report.game.pk, "pk": report.pk, "quote_pk": quote.pk},
    )
    resp = client.post(url)
    assert resp.status_code == 204
    assert not Quote.objects.filter(pk=quote.pk).exists()


@pytest.mark.django_db
def test_quote_delete_non_author_forbidden(client: Client) -> None:
    """POST quote_delete as a non-author → 403, the quote survives."""
    author = UserFactory()
    intruder = UserFactory()
    report = _released_report(author=author)
    quote = _quote(report)

    client.force_login(intruder)
    url = reverse(
        "games:quote_delete",
        kwargs={"game_pk": report.game.pk, "pk": report.pk, "quote_pk": quote.pk},
    )
    resp = client.post(url)

    assert resp.status_code == 403
    assert Quote.objects.filter(pk=quote.pk).exists()
