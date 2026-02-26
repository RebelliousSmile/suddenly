"""
User admin configuration.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "display_name", "email", "remote", "is_staff", "created_at"]
    list_filter = ["remote", "is_staff", "is_active", "content_language", "created_at"]
    search_fields = ["username", "display_name", "email"]
    ordering = ["-created_at"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("display_name", "bio", "avatar")}),
        (
            "Language preferences",
            {"fields": ("content_language", "preferred_languages", "show_unlabeled_content")},
        ),
        (
            "ActivityPub",
            {"fields": ("remote", "ap_id", "inbox_url", "outbox_url", "public_key")},
        ),
    )
