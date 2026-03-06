"""Admin configuration for the activitypub app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin

from .models import FederatedServer

if TYPE_CHECKING:
    _FederatedServerBase = admin.ModelAdmin[FederatedServer]
else:
    _FederatedServerBase = admin.ModelAdmin


@admin.register(FederatedServer)
class FederatedServerAdmin(_FederatedServerBase):
    """Admin for known remote ActivityPub instances."""

    list_display = ["server_name", "application_type", "status", "user_count", "last_checked"]
    list_filter = ["status", "application_type"]
    search_fields = ["server_name"]
    ordering = ["server_name"]
    readonly_fields = ["created_at", "updated_at"]
