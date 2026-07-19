"""
Games API views.
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from suddenly.core.serializers import (
    CharacterSerializer,
    GameCreateSerializer,
    GameSerializer,
    ReportCastSerializer,
    ReportCreateSerializer,
    ReportSerializer,
)
from suddenly.games.models import Game, Report, ReportVisibility
from suddenly.games.services import is_game_master, publish_report


class IsOwnerOrReadOnly(permissions.BasePermission):  # type: ignore[misc]
    """Only owners can modify, anyone can read."""

    def has_object_permission(self, request: Request, view: object, obj: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(obj.owner == request.user)


class GameViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    API endpoint for games.

    list: List all public games
    create: Create a new game
    retrieve: Get game details
    update/partial_update: Update game (owner only)
    delete: Delete game (owner only)
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self) -> QuerySet[Game]:
        queryset = Game.objects.filter(remote=False)

        if self.request.user.is_authenticated:
            # Include user's private games
            return queryset.filter(
                models.Q(is_public=True) | models.Q(owner=self.request.user)
            ).select_related("owner")

        return queryset.filter(is_public=True).select_related("owner")

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action == "create":
            return GameCreateSerializer
        return GameSerializer

    @action(detail=True, methods=["get"])  # type: ignore[untyped-decorator]
    def reports(self, request: Request, pk: str | None = None) -> Response:
        """List reports for this game that have crossed the temporal wall."""
        game = self.get_object()
        reports = game.reports.feed_visible().select_related("author")
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])  # type: ignore[untyped-decorator]
    def characters(self, request: Request, pk: str | None = None) -> Response:
        """List characters from this game."""
        game = self.get_object()
        # Roster = characters homed here; exclude forks (they inherit the parent's
        # origin_game but originated elsewhere). origin_game is still selected:
        # CharacterSerializer exposes origin_game.title.
        characters = game.characters.filter(parent__isnull=True).select_related(
            "owner", "creator", "origin_game"
        )
        serializer = CharacterSerializer(characters, many=True)
        return Response(serializer.data)


class IsAuthorOrReadOnly(permissions.BasePermission):  # type: ignore[misc]
    """Only authors can modify, anyone can read published."""

    def has_object_permission(self, request: Request, view: object, obj: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return bool(obj.status == "published" or obj.author == request.user)
        return bool(obj.author == request.user)


class ReportViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    API endpoint for reports.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self) -> QuerySet[Report]:
        queryset = Report.objects.filter(remote=False)
        params = self.request.query_params

        # The temporal wall gates listings, not just the detail view: a published
        # but unreleased report is behind the wall and must not surface to anyone
        # but its author. `feed_visible()` is the single wall-aware filter.
        visible = Report.objects.feed_visible().values("pk")
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                models.Q(author=self.request.user) | models.Q(pk__in=visible)
            )
        else:
            queryset = queryset.filter(pk__in=visible)

        # Optional query-param filters (all additive)
        if (visibility := params.get("visibility")) and visibility in ReportVisibility.values:
            queryset = queryset.filter(visibility=visibility)

        if game_id := params.get("game"):
            queryset = queryset.filter(game_id=game_id)

        if language := params.get("language"):
            queryset = queryset.filter(language=language)

        return queryset.select_related("author", "game")

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer

    @action(detail=True, methods=["post"])  # type: ignore[untyped-decorator]
    def publish(self, request: Request, pk: str | None = None) -> Response:
        """
        Publish a draft report.

        This will:
        1. Change status to published
        2. Convert ReportCast entries to CharacterAppearance
        3. Create new NPCs from cast entries with new_character_name
        """
        report = self.get_object()

        if report.author != request.user:
            return Response(
                {"error": "Only the author can publish"}, status=status.HTTP_403_FORBIDDEN
            )

        if report.status == "published":
            return Response(
                {"error": "Report is already published"}, status=status.HTTP_400_BAD_REQUEST
            )

        report = publish_report(report, request.user)

        # TODO: Send ActivityPub Create(Note) activity

        serializer = ReportSerializer(report)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"])  # type: ignore[untyped-decorator]
    def cast(self, request: Request, pk: str | None = None) -> Response:
        """
        Manage report cast (characters for this report).

        GET: List cast entries
        POST: Add character to cast
        """
        report = self.get_object()

        if request.method == "GET":
            cast = report.cast.all().select_related("character")
            serializer = ReportCastSerializer(cast, many=True)
            return Response(serializer.data)

        # POST - add to cast
        if report.author != request.user:
            return Response(
                {"error": "Only the author can modify cast"}, status=status.HTTP_403_FORBIDDEN
            )

        # `character` is read-only here, so any POST creates a brand-new NPC —
        # reserved to the game master (an existing NPC is added via the composer).
        if request.data.get("new_character_name") and not is_game_master(request.user, report.game):
            return Response(
                {"error": "Only the game master can create a new NPC"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReportCastSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(report=report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
