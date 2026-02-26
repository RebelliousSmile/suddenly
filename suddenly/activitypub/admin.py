"""Admin configuration for the activitypub app."""

from django.contrib import admin

from .models import FederatedServer


@admin.register(FederatedServer)
class FederatedServerAdmin(admin.ModelAdmin):
    """Admin for known remote ActivityPub instances."""

    list_display = ["server_name", "application_type", "status", "user_count", "last_checked"]
    list_filter = ["status", "application_type"]
    search_fields = ["server_name"]
    ordering = ["server_name"]
    readonly_fields = ["created_at", "updated_at"]
