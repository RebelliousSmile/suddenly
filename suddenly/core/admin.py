"""Admin registration for core models."""

from __future__ import annotations

from django.contrib import admin

from suddenly.core.models import (
    ContentReport,
    DonationPrompt,
    Notification,
    NotificationPreference,
    Tag,
    UserBlock,
    UserMute,
    UserReport,
    UserUsageStats,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["type", "recipient", "actor", "is_read", "created_at"]
    list_filter = ["type", "is_read", "created_at"]
    search_fields = ["recipient__username", "message"]
    raw_id_fields = ["recipient", "actor", "target_content_type"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["category", "reporter", "resolved", "created_at"]
    list_filter = ["category", "resolved", "created_at"]
    search_fields = ["reporter__username", "comment"]
    raw_id_fields = ["reporter", "resolved_by"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["user", "email_link_request", "email_new_report"]
    search_fields = ["user__username"]


@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Secondary consultation surface for UserReport (#136, DEC-F4).

    Primary moderation flow lives in the ``gmh:`` admin surface
    (core.admin_views.admin_reports) — this registration is read-only-ish
    consultation, cheap to add, consistent with ContentReport.
    """

    list_display = ["category", "reporter", "reported_user", "status", "created_at"]
    list_filter = ["category", "status", "created_at"]
    search_fields = ["reporter__username", "reported_user__username", "comment"]
    raw_id_fields = ["reporter", "reported_user", "handled_by"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["blocker", "blocked", "created_at"]
    search_fields = ["blocker__username", "blocked__username"]


@admin.register(UserMute)
class UserMuteAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["muter", "muted", "created_at"]
    search_fields = ["muter__username", "muted__username"]


@admin.register(DonationPrompt)
class DonationPromptAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["user", "posts_at_prompt", "donated", "donated_at", "created_at"]
    list_filter = ["donated", "created_at"]
    search_fields = ["user__username"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UserUsageStats)
class UserUsageStatsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["user", "total_posts", "posts_since_last_prompt", "last_donation_date"]
    search_fields = ["user__username"]
    readonly_fields = ["created_at", "updated_at"]
