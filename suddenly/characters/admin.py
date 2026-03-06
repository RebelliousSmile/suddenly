"""
Characters admin configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin

from .models import (
    Character,
    CharacterAppearance,
    CharacterLink,
    Follow,
    LinkRequest,
    Quote,
    SharedSequence,
)

if TYPE_CHECKING:
    _CharacterBase = admin.ModelAdmin[Character]
    _QuoteBase = admin.ModelAdmin[Quote]
    _AppearanceBase = admin.ModelAdmin[CharacterAppearance]
    _LinkRequestBase = admin.ModelAdmin[LinkRequest]
    _CharacterLinkBase = admin.ModelAdmin[CharacterLink]
    _SharedSequenceBase = admin.ModelAdmin[SharedSequence]
    _FollowBase = admin.ModelAdmin[Follow]
else:
    _CharacterBase = admin.ModelAdmin
    _QuoteBase = admin.ModelAdmin
    _AppearanceBase = admin.ModelAdmin
    _LinkRequestBase = admin.ModelAdmin
    _CharacterLinkBase = admin.ModelAdmin
    _SharedSequenceBase = admin.ModelAdmin
    _FollowBase = admin.ModelAdmin


@admin.register(Character)
class CharacterAdmin(_CharacterBase):
    list_display = ["name", "status", "owner", "creator", "origin_game", "remote", "created_at"]
    list_filter = ["status", "remote", "created_at"]
    search_fields = ["name", "description", "owner__username", "creator__username"]
    raw_id_fields = ["owner", "creator", "origin_game", "parent"]
    ordering = ["-created_at"]


@admin.register(Quote)
class QuoteAdmin(_QuoteBase):
    list_display = ["content_preview", "character", "author", "visibility", "created_at"]
    list_filter = ["visibility", "created_at"]
    search_fields = ["content", "character__name", "author__username"]
    raw_id_fields = ["character", "report", "author"]
    ordering = ["-created_at"]

    @admin.display(description="Content")
    def content_preview(self, obj: Quote) -> str:
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content


@admin.register(CharacterAppearance)
class CharacterAppearanceAdmin(_AppearanceBase):
    list_display = ["character", "report", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["character__name", "report__title"]
    raw_id_fields = ["character", "report"]


@admin.register(LinkRequest)
class LinkRequestAdmin(_LinkRequestBase):
    list_display = ["type", "requester", "target_character", "status", "created_at"]
    list_filter = ["type", "status", "created_at"]
    search_fields = ["requester__username", "target_character__name"]
    raw_id_fields = ["requester", "target_character", "proposed_character"]


@admin.register(CharacterLink)
class CharacterLinkAdmin(_CharacterLinkBase):
    list_display = ["type", "source", "target", "created_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["source__name", "target__name"]
    raw_id_fields = ["source", "target", "link_request"]


@admin.register(SharedSequence)
class SharedSequenceAdmin(_SharedSequenceBase):
    list_display = ["title", "link", "status", "created_at"]
    list_filter = ["status", "created_at"]
    raw_id_fields = ["link"]


@admin.register(Follow)
class FollowAdmin(_FollowBase):
    list_display = ["follower", "content_type", "object_id", "created_at"]
    list_filter = ["content_type", "created_at"]
    search_fields = ["follower__username"]
    raw_id_fields = ["follower"]
