# mypy: disable-error-code="no-untyped-call,type-arg,attr-defined"
"""
Tests for models added/modified in T7.

Covers:
- Report.content_warning and Report.visibility (US-29, US-30)
- Quote.content_warning (US-30)
- LinkRequestStatus QUEUED and EXPIRED (US-15, US-23)
- SharedSequence collaborative fields (DA-3)
- Notification model (US-20)
"""

from __future__ import annotations

from typing import Any

import pytest

from suddenly.characters.models import (
    CharacterLink,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
    SharedSequence,
)
from suddenly.core.models import Notification, NotificationType
from suddenly.games.models import Report, ReportVisibility
from suddenly.users.models import User
from tests.factories import CharacterFactory, GameFactory, UserFactory

# ─── Report CW + Visibility ──────────────────────────────────────


@pytest.mark.django_db
class TestReportVisibility:
    """Test Report visibility and content warning fields."""

    def test_default_visibility_is_public(self, report: Report) -> None:
        assert report.visibility == ReportVisibility.PUBLIC

    def test_can_set_unlisted(self, report: Report) -> None:
        report.visibility = ReportVisibility.UNLISTED
        report.save()
        report.refresh_from_db()
        assert report.visibility == ReportVisibility.UNLISTED

    def test_can_set_followers(self, report: Report) -> None:
        report.visibility = ReportVisibility.FOLLOWERS
        report.save()
        report.refresh_from_db()
        assert report.visibility == ReportVisibility.FOLLOWERS

    def test_content_warning_blank_by_default(self, report: Report) -> None:
        assert report.content_warning == ""

    def test_can_set_content_warning(self, report: Report) -> None:
        report.content_warning = "Violence, thèmes sombres"
        report.save()
        report.refresh_from_db()
        assert report.content_warning == "Violence, thèmes sombres"

    def test_content_warning_max_length(self, report: Report) -> None:
        report.content_warning = "x" * 500
        report.save()  # Should not raise


# ─── Quote CW ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestQuoteCW:
    """Test Quote content warning field."""

    def test_quote_cw_blank_by_default(self, db: Any) -> None:
        from suddenly.characters.models import Quote

        user = UserFactory()  # type: ignore[no-untyped-call]
        game = GameFactory(owner=user)  # type: ignore[no-untyped-call]
        char = CharacterFactory(creator=user, origin_game=game)  # type: ignore[no-untyped-call]
        q = Quote.objects.create(
            content="Test quote",
            character=char,
            author=user,
        )
        assert q.content_warning == ""

    def test_quote_cw_can_be_set(self, db: Any) -> None:
        from suddenly.characters.models import Quote

        user = UserFactory()  # type: ignore[no-untyped-call]
        game = GameFactory(owner=user)  # type: ignore[no-untyped-call]
        char = CharacterFactory(creator=user, origin_game=game)  # type: ignore[no-untyped-call]
        q = Quote.objects.create(
            content="Dark quote",
            character=char,
            author=user,
            content_warning="Contenu mature",
        )
        q.refresh_from_db()
        assert q.content_warning == "Contenu mature"


# ─── LinkRequestStatus QUEUED + EXPIRED ───────────────────────────


@pytest.mark.django_db
class TestLinkRequestStatuses:
    """Test new QUEUED and EXPIRED statuses."""

    def test_queued_status_exists(self) -> None:
        assert LinkRequestStatus.QUEUED == "queued"

    def test_expired_status_exists(self) -> None:
        assert LinkRequestStatus.EXPIRED == "expired"

    def test_can_create_queued_request(self, user: User, character: Any) -> None:
        other = UserFactory()  # type: ignore[no-untyped-call]
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other,
            target_character=character,
            status=LinkRequestStatus.QUEUED,
            message="I want to adopt",
        )
        assert lr.status == LinkRequestStatus.QUEUED

    def test_can_create_expired_request(self, user: User, character: Any) -> None:
        other = UserFactory()  # type: ignore[no-untyped-call]
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other,
            target_character=character,
            status=LinkRequestStatus.EXPIRED,
            message="Timed out",
        )
        assert lr.status == LinkRequestStatus.EXPIRED

    def test_all_statuses_present(self) -> None:
        values = [c[0] for c in LinkRequestStatus.choices]
        assert "pending" in values
        assert "queued" in values
        assert "accepted" in values
        assert "rejected" in values
        assert "cancelled" in values
        assert "expired" in values


# ─── SharedSequence Collaborative Fields ──────────────────────────


@pytest.mark.django_db
class TestSharedSequenceCollab:
    """Test SharedSequence collaborative editing fields."""

    def _create_shared_sequence(self, user: User, character: Any) -> SharedSequence:
        other = UserFactory()  # type: ignore[no-untyped-call]
        lr = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other,
            target_character=character,
            status=LinkRequestStatus.ACCEPTED,
            message="Adopt request",
        )
        link = CharacterLink.objects.create(
            type=LinkType.ADOPT,
            source=character,
            target=character,
            link_request=lr,
        )
        return SharedSequence.objects.create(
            link=link,
            title="Test Sequence",
            content="Markdown content",
        )

    def test_last_edited_by_null_by_default(self, user: User, character: Any) -> None:
        ss = self._create_shared_sequence(user, character)
        assert ss.last_edited_by is None
        assert ss.last_edited_at is None

    def test_publication_proposed_by_null_by_default(self, user: User, character: Any) -> None:
        ss = self._create_shared_sequence(user, character)
        assert ss.publication_proposed_by is None
        assert ss.publication_proposed_at is None

    def test_can_set_last_edited_by(self, user: User, character: Any) -> None:
        from django.utils import timezone

        ss = self._create_shared_sequence(user, character)
        ss.last_edited_by = user
        ss.last_edited_at = timezone.now()
        ss.save()
        ss.refresh_from_db()
        assert ss.last_edited_by == user

    def test_can_propose_publication(self, user: User, character: Any) -> None:
        from django.utils import timezone

        ss = self._create_shared_sequence(user, character)
        ss.publication_proposed_by = user
        ss.publication_proposed_at = timezone.now()
        ss.save()
        ss.refresh_from_db()
        assert ss.publication_proposed_by == user


# ─── Notification Model ──────────────────────────────────────────


@pytest.mark.django_db
class TestNotification:
    """Test Notification model (US-20)."""

    def test_create_notification(self, user: User) -> None:
        n = Notification.objects.create(
            recipient=user,
            type=NotificationType.LINK_REQUEST,
            message="@bob veut adopter votre PNJ Viktor",
        )
        assert n.is_read is False
        assert n.recipient == user
        assert n.type == NotificationType.LINK_REQUEST

    def test_notification_with_actor(self, user: User, other_user: User) -> None:
        n = Notification.objects.create(
            recipient=user,
            type=NotificationType.NEW_FOLLOWER,
            actor=other_user,
            message=f"@{other_user.username} vous suit",
        )
        assert n.actor == other_user

    def test_notification_with_target(self, user: User, character: Any) -> None:
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(character)
        n = Notification.objects.create(
            recipient=user,
            type=NotificationType.LINK_REQUEST,
            message="Demande sur Viktor",
            target_content_type=ct,
            target_object_id=character.id,
        )
        assert n.target == character

    def test_mark_as_read(self, user: User) -> None:
        n = Notification.objects.create(
            recipient=user,
            type=NotificationType.NEW_REPORT,
            message="Nouveau CR",
        )
        assert not n.is_read
        n.is_read = True
        n.save()
        n.refresh_from_db()
        assert n.is_read

    def test_all_notification_types(self) -> None:
        assert len(NotificationType.choices) == 10

    def test_notification_ordering(self, user: User) -> None:
        """Notifications are ordered by -created_at."""
        Notification.objects.create(
            recipient=user,
            type=NotificationType.NEW_REPORT,
            message="First",
        )
        n2 = Notification.objects.create(
            recipient=user,
            type=NotificationType.NEW_FOLLOWER,
            message="Second",
        )
        notifs = list(Notification.objects.filter(recipient=user))
        assert notifs[0].id == n2.id  # Most recent first

    def test_unread_count(self, user: User) -> None:
        Notification.objects.create(recipient=user, type=NotificationType.MENTION, message="M1")
        Notification.objects.create(
            recipient=user, type=NotificationType.MENTION, message="M2", is_read=True
        )
        Notification.objects.create(recipient=user, type=NotificationType.INVITATION, message="M3")
        unread = Notification.objects.filter(recipient=user, is_read=False).count()
        assert unread == 2
