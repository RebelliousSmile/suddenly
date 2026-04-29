"""Tests for RapportLink model — clean() validation and DB constraints."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from suddenly.games.models import RapportLink
from tests.factories import RapportFactory, ReportFactory, UserFactory


@pytest.mark.django_db
class TestRapportLinkClean:
    """Unit tests for RapportLink.clean() — exactly one parent must be set."""

    def test_both_parent_rapport_and_parent_iri_raises(self) -> None:
        """Setting both parent_rapport and parent_iri must raise ValidationError."""
        user = UserFactory()
        report = ReportFactory(author=user)
        parent = RapportFactory(report=report)
        child = RapportFactory(report=report)

        link = RapportLink(
            rapport=child,
            parent_rapport=parent,
            parent_iri="https://example.com/rapports/abc",
        )
        with pytest.raises(ValidationError):
            link.clean()

    def test_neither_parent_rapport_nor_parent_iri_raises(self) -> None:
        """Setting neither parent_rapport nor parent_iri must raise ValidationError."""
        user = UserFactory()
        report = ReportFactory(author=user)
        child = RapportFactory(report=report)

        link = RapportLink(rapport=child, parent_rapport=None, parent_iri=None)
        with pytest.raises(ValidationError):
            link.clean()

    def test_parent_rapport_set_parent_iri_none_valid(self) -> None:
        """Setting parent_rapport only must be valid (no exception raised)."""
        user = UserFactory()
        report = ReportFactory(author=user)
        parent = RapportFactory(report=report)
        child = RapportFactory(report=report)

        link = RapportLink(rapport=child, parent_rapport=parent, parent_iri=None)
        # Must not raise
        link.clean()

    def test_parent_iri_set_parent_rapport_none_valid(self) -> None:
        """Setting parent_iri only must be valid (no exception raised)."""
        user = UserFactory()
        report = ReportFactory(author=user)
        child = RapportFactory(report=report)

        link = RapportLink(rapport=child, parent_rapport=None, parent_iri="https://example.com/r/1")
        # Must not raise
        link.clean()

    def test_duplicate_local_parent_raises_db_constraint(self) -> None:
        """Creating two RapportLink rows with the same (rapport, parent_rapport) must fail."""
        user = UserFactory()
        report = ReportFactory(author=user)
        parent = RapportFactory(report=report)
        child = RapportFactory(report=report)

        link1 = RapportLink(rapport=child, parent_rapport=parent)
        link1.full_clean()
        link1.save()

        link2 = RapportLink(rapport=child, parent_rapport=parent)
        with pytest.raises((IntegrityError, ValidationError)):
            link2.full_clean()
            link2.save()
