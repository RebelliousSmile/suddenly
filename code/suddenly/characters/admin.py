"""
Characters admin configuration.
"""

from django.contrib import admin

from .models import (
    Character,
    Quote,
    CharacterAppearance,
    LinkRequest,
    CharacterLink,
    SharedSequence,
    Follow,
)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "owner", "creator", "origin_game", "remote", "created_at"]
    list_filter = ["status", "remote", "created_at"]
    search_fields = ["name", "description", "owner__username", "creator__username"]
    raw_id_fields = ["owner", "creator", "origin_game", "parent"]
    ordering = ["-created_at"]


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ["content_preview", "character", "author", "visibility", "created_at"]
    list_filter = ["visibility", "created_at"]
    search_fields = ["content", "character__name", "author__username"]
    raw_id_fields = ["character", "report", "author"]
    ordering = ["-created_at"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(CharacterAppearance)
class CharacterAppearanceAdmin(admin.ModelAdmin):
    list_display = ["character", "report", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["character__name", "report__title"]
    raw_id_fields = ["character", "report"]


@admin.register(LinkRequest)
class LinkRequestAdmin(admin.ModelAdmin):
    list_display = ["type", "requester", "target_character", "status", "created_at"]
    list_filter = ["type", "status", "created_at"]
    search_fields = ["requester__username", "target_character__name"]
    raw_id_fields = ["requester", "target_character", "proposed_character"]


@admin.register(CharacterLink)
class CharacterLinkAdmin(admin.ModelAdmin):
    list_display = ["type", "source", "target", "created_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["source__name", "target__name"]
    raw_id_fields = ["source", "target", "link_request"]


@admin.register(SharedSequence)
class SharedSequenceAdmin(admin.ModelAdmin):
    list_display = ["title", "link", "status", "created_at"]
    list_filter = ["status", "created_at"]
    raw_id_fields = ["link"]


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "target_type", "target_id", "created_at"]
    list_filter = ["target_type", "created_at"]
    search_fields = ["follower__username"]
    raw_id_fields = ["follower"]_fields = ["requester__username", "target_character__name", "message"]
    raw_id_fields = ["requester", "target_character", "proposed_character"]


@admin.register(CharacterLink)
class CharacterLinkAdmin(admin.ModelAdmin):
    list_display = ["type", "source", "target", "created_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["source__name", "target__name"]
    raw_id_fields = ["source", "target", "link_request"]


@admin.register(SharedSequence)
class SharedSequenceAdmin(admin.ModelAdmin):
    list_display = ["title", "link", "status", "created_at"]
    list_filter = ["status", "created_at"]
    raw_id_fields = ["link"]


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "target_type", "target_id", "created_at"]
    list_filter = ["target_type", "created_at"]
    search_fields = ["follower__username"]
    raw_id_fields = ["follower"]
