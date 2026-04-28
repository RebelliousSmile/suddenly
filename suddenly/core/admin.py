"""Admin registration for core models."""

from __future__ import annotations

from django.contrib import admin

from suddenly.core.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["type", "recipient", "actor", "is_read", "created_at"]
    list_filter = ["type", "is_read", "created_at"]
    search_fields = ["recipient__username", "message"]
    raw_id_fields = ["recipient", "actor", "target_content_type"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
