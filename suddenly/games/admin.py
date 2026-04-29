"""
Games admin configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin

from .models import Game, GameSystem, Rapport, RapportMarker, Report, ReportCast

if TYPE_CHECKING:
    _GameSystemBase = admin.ModelAdmin[GameSystem]
    _GameBase = admin.ModelAdmin[Game]
    _ReportBase = admin.ModelAdmin[Report]
    _ReportCastBase = admin.ModelAdmin[ReportCast]
    _ReportCastInlineBase = admin.TabularInline[ReportCast, Report]
    _RapportInlineBase = admin.TabularInline[Rapport, Report]
    _RapportMarkerInlineBase = admin.TabularInline[RapportMarker, Report]
else:
    _GameSystemBase = admin.ModelAdmin
    _GameBase = admin.ModelAdmin
    _ReportBase = admin.ModelAdmin
    _ReportCastBase = admin.ModelAdmin
    _ReportCastInlineBase = admin.TabularInline
    _RapportInlineBase = admin.TabularInline
    _RapportMarkerInlineBase = admin.TabularInline


@admin.register(GameSystem)
class GameSystemAdmin(_GameSystemBase):
    """Admin for GameSystem — game rule systems catalog."""

    list_display = ["slug", "name", "git_url", "is_deprecated", "synced_at"]
    search_fields = ["slug", "name"]


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
    fields = ["kind", "actor", "content"]
    extra = 0


class RapportMarkerInline(_RapportMarkerInlineBase):
    model = RapportMarker
    fields = ["kind", "character"]
    extra = 0


@admin.register(Report)
class ReportAdmin(_ReportBase):
    list_display = ["title", "game", "author", "status", "published_at", "created_at"]
    list_filter = ["status", "remote", "created_at", "published_at"]
    search_fields = ["title", "content", "game__title", "author__username"]
    raw_id_fields = ["game", "author"]
    ordering = ["-created_at"]
    inlines = [ReportCastInline, RapportInline]


@admin.register(ReportCast)
class ReportCastAdmin(_ReportCastBase):
    list_display = ["report", "character", "new_character_name", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["report__title", "character__name", "new_character_name"]
    raw_id_fields = ["report", "character"]
