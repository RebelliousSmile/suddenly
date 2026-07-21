"""
Tests for user reporting & instance moderation (Epic F, #136).

Covers the 4 epic-level acceptance criteria (see Phase 5 of
`aidd_docs/tasks/2026_07/2026_07_19-136-epic-f-reporting-moderation.md`):
1. A user reports another with a mandatory reason -> `UserReport` created
   - `TestCreateUserReport`, `TestReportUserView`.
2. An admin sees the pending queue and can block/dismiss -> `TestAdminReportsQueue`,
   `TestAdminReportDismiss`, `TestAdminUserBlock`, `TestAdminUserUnblock`.
3. (local volet) covered by `tests/characters/test_follow_gating.py`; (federated
   volet) covered by `tests/activitypub/test_block_gating.py`.
4. The reported user is never notified -> `TestReportedUserNeverNotified`.

Also covers the `core.moderation` service in isolation (`TestIsBlocked`,
`TestBlockUser`, `TestUnblockUser`, `TestCreateUserReportService`) and the
admin-notification signal (`TestNotifyAdminsOnUserReport`).
"""

from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import Character
from suddenly.core.models import (
    Notification,
    NotificationType,
    ReportCategory,
    UserReport,
    UserReportStatus,
)
from suddenly.core.moderation import (
    block_user,
    create_user_report,
    is_blocked,
    unblock_user,
)
from tests.factories import CharacterFactory, GameFactory, ReportFactory, UserFactory

# ─── core.moderation service ───────────────────────────────────────────────


@pytest.mark.django_db
class TestIsBlocked:
    def test_default_user_not_blocked(self) -> None:
        user = UserFactory()
        assert is_blocked(user) is False

    def test_blocked_user_reports_true(self) -> None:
        user = UserFactory(is_blocked=True)
        assert is_blocked(user) is True

    def test_tolerant_to_object_without_is_blocked_attribute(self) -> None:
        class Bare:
            pass

        assert is_blocked(Bare()) is False


@pytest.mark.django_db
class TestBlockUser:
    def test_block_user_sets_flag_and_audit(self) -> None:
        target = UserFactory()
        admin = UserFactory(is_admin=True)

        block_user(target, by=admin)
        target.refresh_from_db()

        assert target.is_blocked is True
        assert target.blocked_at is not None
        assert target.blocked_by_admin_id == admin.pk

    def test_block_user_is_idempotent(self) -> None:
        target = UserFactory()
        admin = UserFactory(is_admin=True)

        block_user(target, by=admin)
        target.refresh_from_db()
        first_blocked_at = target.blocked_at

        block_user(target, by=admin)
        target.refresh_from_db()

        assert target.blocked_at == first_blocked_at

    def test_block_user_resolves_given_report(self) -> None:
        reporter = UserFactory()
        target = UserFactory()
        admin = UserFactory(is_admin=True)
        report = create_user_report(reporter, target, ReportCategory.HARASSMENT)

        block_user(target, by=admin, report=report)
        report.refresh_from_db()

        assert report.status == UserReportStatus.RESOLVED
        assert report.handled_by_id == admin.pk
        assert report.handled_at is not None

    def test_block_user_without_report_does_not_touch_other_reports(self) -> None:
        reporter = UserFactory()
        target = UserFactory()
        admin = UserFactory(is_admin=True)
        report = create_user_report(reporter, target, ReportCategory.SPAM)

        block_user(target, by=admin)
        report.refresh_from_db()

        assert report.status == UserReportStatus.PENDING


@pytest.mark.django_db
class TestUnblockUser:
    def test_unblock_user_resets_flag_and_audit(self) -> None:
        admin = UserFactory(is_admin=True)
        target = UserFactory()
        block_user(target, by=admin)
        target.refresh_from_db()

        unblock_user(target)
        target.refresh_from_db()

        assert target.is_blocked is False
        assert target.blocked_at is None
        assert target.blocked_by_admin_id is None

    def test_unblock_user_is_idempotent_noop_on_unblocked_user(self) -> None:
        target = UserFactory()

        unblock_user(target)
        target.refresh_from_db()

        assert target.is_blocked is False


@pytest.mark.django_db
class TestCreateUserReportService:
    def test_creates_pending_report_with_reason(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()

        report = create_user_report(reporter, reported, ReportCategory.SPAM, comment="Ads.")

        assert report.status == UserReportStatus.PENDING
        assert report.reporter_id == reporter.pk
        assert report.reported_user_id == reported.pk
        assert report.category == ReportCategory.SPAM
        assert report.comment == "Ads."

    def test_self_report_raises_value_error(self) -> None:
        user = UserFactory()

        with pytest.raises(ValueError, match="cannot report themselves"):
            create_user_report(user, user, ReportCategory.OTHER)

        assert UserReport.objects.count() == 0

    def test_context_gfk_is_recorded(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()
        character = CharacterFactory()

        report = create_user_report(
            reporter, reported, ReportCategory.INAPPROPRIATE, context=character
        )

        character_ct = ContentType.objects.get_for_model(Character)
        assert report.context_content_type_id == character_ct.pk
        assert report.context_object_id == character.pk

    def test_context_optional(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()

        report = create_user_report(reporter, reported, ReportCategory.OTHER)

        assert report.context_content_type_id is None
        assert report.context_object_id is None


# ─── admin notification signal (DEC-F5 / DEC-F6) ───────────────────────────


@pytest.mark.django_db
class TestNotifyAdminsOnUserReport:
    def test_notifies_every_local_admin(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()
        admin1 = UserFactory(is_admin=True)
        admin2 = UserFactory(is_admin=True)
        UserFactory(is_admin=False)  # not an admin -> not notified

        create_user_report(reporter, reported, ReportCategory.SPAM)

        notifs = Notification.objects.filter(type=NotificationType.MODERATION_REPORT)
        recipients = set(notifs.values_list("recipient_id", flat=True))
        assert recipients == {admin1.pk, admin2.pk}
        for notif in notifs:
            assert notif.actor_id == reporter.pk

    def test_does_not_notify_remote_admin(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()
        UserFactory(is_admin=True, remote=True, ap_id="https://peer.example/users/remote-admin")

        create_user_report(reporter, reported, ReportCategory.SPAM)

        notifs = Notification.objects.filter(type=NotificationType.MODERATION_REPORT)
        assert notifs.count() == 0

    def test_no_admins_creates_no_notification_and_does_not_raise(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()

        create_user_report(reporter, reported, ReportCategory.SPAM)

        assert Notification.objects.filter(type=NotificationType.MODERATION_REPORT).count() == 0


# ─── critère 4 : le signalé n'est JAMAIS notifié ───────────────────────────


@pytest.mark.django_db
class TestReportedUserNeverNotified:
    def test_reported_user_receives_zero_notifications_on_report(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()
        UserFactory(is_admin=True)

        create_user_report(reporter, reported, ReportCategory.HARASSMENT)

        assert Notification.objects.filter(recipient=reported).count() == 0

    def test_reported_user_receives_zero_notifications_on_block(self) -> None:
        reporter = UserFactory()
        reported = UserFactory()
        admin = UserFactory(is_admin=True)
        report = create_user_report(reporter, reported, ReportCategory.HARASSMENT)

        block_user(reported, by=admin, report=report)

        assert Notification.objects.filter(recipient=reported).count() == 0

    def test_reporting_a_local_admin_does_not_notify_that_admin(self) -> None:
        reporter = UserFactory()
        reported_admin = UserFactory(is_admin=True)
        other_admin = UserFactory(is_admin=True)

        create_user_report(reporter, reported_admin, ReportCategory.HARASSMENT)

        notifs = Notification.objects.filter(type=NotificationType.MODERATION_REPORT)
        recipients = set(notifs.values_list("recipient_id", flat=True))
        assert reported_admin.pk not in recipients
        assert recipients == {other_admin.pk}


# ─── report_user view (critère 1, user-facing) ─────────────────────────────


@pytest.mark.django_db
class TestReportUserView:
    def test_get_renders_form(self) -> None:
        reported = UserFactory()
        reporter = UserFactory()
        client = Client()
        client.force_login(reporter)

        response = client.get(reverse("core:report_user", kwargs={"username": reported.username}))

        assert response.status_code == 200
        assert reported.username.encode() in response.content

    def test_anonymous_redirected_to_login(self) -> None:
        reported = UserFactory()
        client = Client()

        response = client.get(reverse("core:report_user", kwargs={"username": reported.username}))

        assert response.status_code == 302
        assert "login" in response.url

    def test_post_creates_pending_report_and_redirects(self) -> None:
        reported = UserFactory()
        reporter = UserFactory()
        client = Client()
        client.force_login(reporter)

        response = client.post(
            reverse("core:report_user", kwargs={"username": reported.username}),
            {"category": ReportCategory.SPAM, "comment": "Unwanted ads."},
        )

        assert response.status_code == 302
        report = UserReport.objects.get(reporter=reporter, reported_user=reported)
        assert report.status == UserReportStatus.PENDING
        assert report.category == ReportCategory.SPAM
        assert report.comment == "Unwanted ads."

    def test_self_report_rejected_no_report_created(self) -> None:
        user = UserFactory()
        client = Client()
        client.force_login(user)

        response = client.post(
            reverse("core:report_user", kwargs={"username": user.username}),
            {"category": ReportCategory.SPAM, "comment": ""},
        )

        assert response.status_code == 200
        assert UserReport.objects.count() == 0

    def test_missing_category_rejected_no_report_created(self) -> None:
        reported = UserFactory()
        reporter = UserFactory()
        client = Client()
        client.force_login(reporter)

        response = client.post(
            reverse("core:report_user", kwargs={"username": reported.username}),
            {"category": "", "comment": ""},
        )

        assert response.status_code == 200
        assert UserReport.objects.count() == 0

    def test_unknown_username_returns_404(self) -> None:
        reporter = UserFactory()
        client = Client()
        client.force_login(reporter)

        response = client.get(reverse("core:report_user", kwargs={"username": "ghost-user"}))

        assert response.status_code == 404


# ─── admin moderation queue (critère 2) ─────────────────────────────────────


@pytest.mark.django_db
class TestAdminReportsQueue:
    def test_admin_sees_pending_reports(self) -> None:
        admin = UserFactory(is_admin=True)
        reporter = UserFactory()
        reported = UserFactory()
        create_user_report(reporter, reported, ReportCategory.SPAM)
        client = Client()
        client.force_login(admin)

        response = client.get(reverse("gmh:reports"))

        assert response.status_code == 200
        assert reported.username.encode() in response.content

    def test_queue_links_to_flagged_content(self) -> None:
        """A signalement carrying a content context surfaces a link to that
        element in the queue, so the admin can retrieve it fast (#150)."""
        admin = UserFactory(is_admin=True)
        reporter = UserFactory()
        scene = ReportFactory()
        create_user_report(reporter, scene.author, ReportCategory.INAPPROPRIATE, context=scene)
        client = Client()
        client.force_login(admin)

        response = client.get(reverse("gmh:reports"))

        detail_url = reverse(
            "games:report_detail", kwargs={"game_pk": scene.game_id, "pk": scene.pk}
        )
        assert detail_url.encode() in response.content

    def test_resolved_and_dismissed_reports_excluded_from_queue(self) -> None:
        admin = UserFactory(is_admin=True)
        reporter = UserFactory()
        dismissed_target = UserFactory()
        report = create_user_report(reporter, dismissed_target, ReportCategory.OTHER)
        report.status = UserReportStatus.DISMISSED
        report.save(update_fields=["status"])
        client = Client()
        client.force_login(admin)

        response = client.get(reverse("gmh:reports"))

        assert dismissed_target.username.encode() not in response.content

    def test_non_admin_redirected(self) -> None:
        non_admin = UserFactory(is_admin=False)
        client = Client()
        client.force_login(non_admin)

        response = client.get(reverse("gmh:reports"))

        assert response.status_code == 302

    def test_anonymous_redirected(self) -> None:
        client = Client()

        response = client.get(reverse("gmh:reports"))

        assert response.status_code == 302


@pytest.mark.django_db
class TestAdminReportDismiss:
    def test_admin_dismisses_pending_report(self) -> None:
        admin = UserFactory(is_admin=True)
        reporter = UserFactory()
        reported = UserFactory()
        report = create_user_report(reporter, reported, ReportCategory.SPAM)
        client = Client()
        client.force_login(admin)

        response = client.post(reverse("gmh:report_dismiss", kwargs={"pk": report.pk}))

        assert response.status_code == 302
        report.refresh_from_db()
        assert report.status == UserReportStatus.DISMISSED
        assert report.handled_by_id == admin.pk
        assert report.handled_at is not None
        reported.refresh_from_db()
        assert reported.is_blocked is False

    def test_get_not_allowed(self) -> None:
        admin = UserFactory(is_admin=True)
        reporter = UserFactory()
        reported = UserFactory()
        report = create_user_report(reporter, reported, ReportCategory.SPAM)
        client = Client()
        client.force_login(admin)

        response = client.get(reverse("gmh:report_dismiss", kwargs={"pk": report.pk}))

        assert response.status_code == 405

    def test_non_admin_cannot_dismiss(self) -> None:
        non_admin = UserFactory(is_admin=False)
        reporter = UserFactory()
        reported = UserFactory()
        report = create_user_report(reporter, reported, ReportCategory.SPAM)
        client = Client()
        client.force_login(non_admin)

        response = client.post(reverse("gmh:report_dismiss", kwargs={"pk": report.pk}))

        assert response.status_code == 302
        report.refresh_from_db()
        assert report.status == UserReportStatus.PENDING


@pytest.mark.django_db
class TestAdminUserBlock:
    def test_admin_blocks_reported_user_and_resolves_report(self) -> None:
        admin = UserFactory(is_admin=True)
        reporter = UserFactory()
        reported = UserFactory()
        report = create_user_report(reporter, reported, ReportCategory.HARASSMENT)
        client = Client()
        client.force_login(admin)

        response = client.post(reverse("gmh:user_block", kwargs={"pk": report.pk}))

        assert response.status_code == 302
        reported.refresh_from_db()
        assert reported.is_blocked is True
        assert reported.blocked_by_admin_id == admin.pk
        report.refresh_from_db()
        assert report.status == UserReportStatus.RESOLVED

    def test_get_not_allowed(self) -> None:
        admin = UserFactory(is_admin=True)
        reporter = UserFactory()
        reported = UserFactory()
        report = create_user_report(reporter, reported, ReportCategory.HARASSMENT)
        client = Client()
        client.force_login(admin)

        response = client.get(reverse("gmh:user_block", kwargs={"pk": report.pk}))

        assert response.status_code == 405

    def test_non_admin_cannot_block(self) -> None:
        non_admin = UserFactory(is_admin=False)
        reporter = UserFactory()
        reported = UserFactory()
        report = create_user_report(reporter, reported, ReportCategory.HARASSMENT)
        client = Client()
        client.force_login(non_admin)

        response = client.post(reverse("gmh:user_block", kwargs={"pk": report.pk}))

        assert response.status_code == 302
        reported.refresh_from_db()
        assert reported.is_blocked is False


@pytest.mark.django_db
class TestAdminUserUnblock:
    def test_admin_unblocks_user(self) -> None:
        admin = UserFactory(is_admin=True)
        target = UserFactory()
        block_user(target, by=admin)
        client = Client()
        client.force_login(admin)

        response = client.post(reverse("gmh:user_unblock", kwargs={"pk": target.pk}))

        assert response.status_code == 302
        target.refresh_from_db()
        assert target.is_blocked is False

    def test_get_not_allowed(self) -> None:
        admin = UserFactory(is_admin=True)
        target = UserFactory()
        client = Client()
        client.force_login(admin)

        response = client.get(reverse("gmh:user_unblock", kwargs={"pk": target.pk}))

        assert response.status_code == 405

    def test_non_admin_cannot_unblock(self) -> None:
        non_admin = UserFactory(is_admin=False)
        admin = UserFactory(is_admin=True)
        target = UserFactory()
        block_user(target, by=admin)
        client = Client()
        client.force_login(non_admin)

        response = client.post(reverse("gmh:user_unblock", kwargs={"pk": target.pk}))

        assert response.status_code == 302
        target.refresh_from_db()
        assert target.is_blocked is True


# ─── is_active suspension stays orthogonal to is_blocked (DEC-F2) ─────────


@pytest.mark.django_db
class TestBlockDistinctFromSuspend:
    def test_blocking_does_not_change_is_active(self) -> None:
        admin = UserFactory(is_admin=True)
        target = UserFactory()

        block_user(target, by=admin)
        target.refresh_from_db()

        assert target.is_active is True
        assert target.is_blocked is True

    def test_admin_user_suspend_does_not_set_is_blocked(self) -> None:
        admin = UserFactory(is_admin=True)
        target = UserFactory()
        client = Client()
        client.force_login(admin)

        client.post(reverse("gmh:user_suspend", kwargs={"pk": target.pk}))

        target.refresh_from_db()
        assert target.is_active is False
        assert target.is_blocked is False


# ─── report_content view — signaler un contenu (#150, Option A) ─────────────


@pytest.mark.django_db
class TestReportContentView:
    def test_report_scene_files_report_against_author_with_context(self) -> None:
        reporter = UserFactory()
        scene = ReportFactory()
        client = Client()
        client.force_login(reporter)

        response = client.post(
            reverse("core:report_content", kwargs={"kind": "scene", "pk": scene.pk}),
            {"category": ReportCategory.INAPPROPRIATE, "comment": "Not ok."},
        )

        assert response.status_code == 302
        report = UserReport.objects.get(reporter=reporter, reported_user=scene.author)
        assert report.status == UserReportStatus.PENDING
        assert report.context == scene  # the flagged element is recorded

    def test_report_character_targets_owner_or_creator(self) -> None:
        reporter = UserFactory()
        character = CharacterFactory()  # owner null → responsible party is the creator
        client = Client()
        client.force_login(reporter)

        response = client.post(
            reverse("core:report_content", kwargs={"kind": "character", "pk": character.pk}),
            {"category": ReportCategory.HARASSMENT, "comment": ""},
        )

        assert response.status_code == 302
        report = UserReport.objects.get(reporter=reporter, reported_user=character.creator)
        assert report.context == character

    def test_report_game_targets_owner(self) -> None:
        reporter = UserFactory()
        game = GameFactory()
        client = Client()
        client.force_login(reporter)

        response = client.post(
            reverse("core:report_content", kwargs={"kind": "game", "pk": game.pk}),
            {"category": ReportCategory.SPAM, "comment": ""},
        )

        assert response.status_code == 302
        report = UserReport.objects.get(reporter=reporter, reported_user=game.owner)
        assert report.context == game

    def test_reporting_own_content_creates_no_report(self) -> None:
        author = UserFactory()
        scene = ReportFactory(author=author)
        client = Client()
        client.force_login(author)

        response = client.post(
            reverse("core:report_content", kwargs={"kind": "scene", "pk": scene.pk}),
            {"category": ReportCategory.SPAM, "comment": ""},
        )

        assert response.status_code == 302  # redirected back, not a form re-render
        assert UserReport.objects.count() == 0

    def test_unknown_kind_returns_404(self) -> None:
        reporter = UserFactory()
        client = Client()
        client.force_login(reporter)

        response = client.get(
            reverse("core:report_content", kwargs={"kind": "widget", "pk": reporter.pk})
        )

        assert response.status_code == 404

    def test_anonymous_redirected_to_login(self) -> None:
        scene = ReportFactory()
        client = Client()

        response = client.get(
            reverse("core:report_content", kwargs={"kind": "scene", "pk": scene.pk})
        )

        assert response.status_code == 302
        assert "login" in response.url
