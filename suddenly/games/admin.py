"""
Games admin configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin

from .models import (
    Game,
    GameCast,
    Rapport,
    RapportLink,
    RapportMarker,
    RapportMedia,
    Report,
    ReportCast,
)

if TYPE_CHECKING:
    _GameBase = admin.ModelAdmin[Game]
    _GameCastBase = admin.ModelAdmin[GameCast]
    _ReportBase = admin.ModelAdmin[Report]
    _ReportCastBase = admin.ModelAdmin[ReportCast]
    _RapportAdminBase = admin.ModelAdmin[Rapport]
    _ReportCastInlineBase = admin.TabularInline[ReportCast, Report]
    _RapportInlineBase = admin.TabularInline[Rapport, Report]
    _RapportMarkerInlineBase = admin.TabularInline[RapportMarker, Report]
    _RapportLinkInlineBase = admin.TabularInline[RapportLink, Rapport]
    _RapportMediaInlineBase = admin.TabularInline[RapportMedia, Rapport]
else:
    _GameBase = admin.ModelAdmin
    _GameCastBase = admin.ModelAdmin
    _ReportBase = admin.ModelAdmin
    _ReportCastBase = admin.ModelAdmin
    _RapportAdminBase = admin.ModelAdmin
    _ReportCastInlineBase = admin.TabularInline
    _RapportInlineBase = admin.TabularInline
    _RapportMarkerInlineBase = admin.TabularInline
    _RapportLinkInlineBase = admin.TabularInline
    _RapportMediaInlineBase = admin.TabularInline


@admin.register(Game)
class GameAdmin(_GameBase):
    list_display = ["title", "owner", "game_system", "is_public", "remote", "created_at"]
    list_filter = ["is_public", "remote", "game_system", "created_at"]
    search_fields = ["title", "description", "owner__username"]
    raw_id_fields = ["owner"]
    ordering = ["-created_at"]


class ReportCastInline(_ReportCastInlineBase):
    model = ReportCast
    extra = 0
    raw_id_fields = ["character"]


class RapportInline(_RapportInlineBase):
    model = Rapport
    fields = ["kind", "status", "actor", "content"]
    extra = 0


class RapportMediaInline(_RapportMediaInlineBase):
    model = RapportMedia
    fields = ["image", "alt"]
    extra = 0


class RapportMarkerInline(_RapportMarkerInlineBase):
    model = RapportMarker
    fields = ["kind", "character"]
    extra = 0


class RapportLinkInline(_RapportLinkInlineBase):
    model = RapportLink
    fk_name = "rapport"
    fields = ["parent_rapport", "parent_iri"]
    extra = 0
    raw_id_fields = ["parent_rapport"]


@admin.register(Report)
class ReportAdmin(_ReportBase):
    list_display = ["title", "game", "author", "status", "published_at", "created_at"]
    list_filter = ["status", "remote", "created_at", "published_at"]
    search_fields = ["title", "content", "game__title", "author__username"]
    raw_id_fields = ["game", "author"]
    ordering = ["-created_at"]
    inlines = [ReportCastInline, RapportInline]


@admin.register(Rapport)
class RapportAdmin(_RapportAdminBase):
    list_display = ["__str__", "report", "kind", "status", "created_at"]
    list_filter = ["kind", "status", "created_at"]
    search_fields = ["content", "report__title"]
    raw_id_fields = ["report", "actor"]
    ordering = ["-created_at"]
    inlines = [RapportLinkInline, RapportMediaInline]


@admin.register(GameCast)
class GameCastAdmin(_GameCastBase):
    list_display = ["game", "character", "added_by", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["game__title", "character__name"]
    raw_id_fields = ["game", "character", "added_by"]
    ordering = ["-created_at"]


@admin.register(ReportCast)
class ReportCastAdmin(_ReportCastBase):
    list_display = ["report", "character", "new_character_name", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["report__title", "character__name", "new_character_name"]
    raw_id_fields = ["report", "character"]
