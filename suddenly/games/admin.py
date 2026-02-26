"""
Games admin configuration.
"""

from django.contrib import admin

from .models import Game, Report, ReportCast


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "game_system", "is_public", "remote", "created_at"]
    list_filter = ["is_public", "remote", "game_system", "created_at"]
    search_fields = ["title", "description", "owner__username"]
    raw_id_fields = ["owner"]
    ordering = ["-created_at"]


class ReportCastInline(admin.TabularInline):
    model = ReportCast
    extra = 0
    raw_id_fields = ["character"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["title", "game", "author", "status", "published_at", "created_at"]
    list_filter = ["status", "remote", "created_at", "published_at"]
    search_fields = ["title", "content", "game__title", "author__username"]
    raw_id_fields = ["game", "author"]
    ordering = ["-created_at"]
    inlines = [ReportCastInline]


@admin.register(ReportCast)
class ReportCastAdmin(admin.ModelAdmin):
    list_display = ["report", "character", "new_character_name", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["report__title", "character__name", "new_character_name"]
    raw_id_fields = ["report", "character"]
