"""
Characters API views with Claim/Adopt/Fork logic.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from suddenly.characters.models import (
    Character,
    CharacterLink,
    CharacterStatus,
    Follow,
    LinkRequest,
    LinkType,
)
from suddenly.characters.services import LinkService, build_character_queryset
from suddenly.core.serializers import (
    CharacterDetailSerializer,
    CharacterLinkSerializer,
    CharacterSearchSerializer,
    CharacterSerializer,
    FollowSerializer,
    LinkRequestCreateSerializer,
    LinkRequestSerializer,
)


class CharacterViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    API endpoint for characters.

    Includes Claim, Adopt, Fork actions.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self) -> QuerySet[Character]:
        queryset = Character.objects.filter(remote=False)

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by game
        game_id = self.request.query_params.get("game")
        if game_id:
            queryset = queryset.filter(origin_game_id=game_id)

        # Filter available NPCs
        if self.request.query_params.get("available") == "true":
            queryset = queryset.filter(status=CharacterStatus.NPC)

        return queryset.select_related("owner", "creator", "origin_game")

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action == "retrieve":
            return CharacterDetailSerializer
        if self.action == "search":
            return CharacterSearchSerializer
        return CharacterSerializer

    @action(detail=False, methods=["get"])  # type: ignore[untyped-decorator]
    def search(self, request: Request, **kwargs: Any) -> Response:
        """
        Search characters for @mention autocomplete.

        Query params:
        - q: Search query (name)
        - limit: Max results (default 10)
        """
        query = request.query_params.get("q", "")
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))  # clamp: never crash, never unbounded

        if len(query) < 2:
            return Response([])

        characters = build_character_queryset(q=query)[:limit]

        serializer = CharacterSearchSerializer(characters, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])  # type: ignore[untyped-decorator]
    def appearances(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """List reports where this character appears."""
        character = self.get_object()
        from suddenly.games.models import Report

        appearances = character.appearances.select_related(
            "report", "report__author", "report__game"
        ).filter(report__in=Report.objects.feed_visible())

        data = [
            {
                "report_id": a.report.id,
                "report_title": a.report.title,
                "game_title": a.report.game.title,
                "role": a.role,
                "published_at": a.report.published_at,
            }
            for a in appearances
        ]

        return Response(data)

    @action(detail=True, methods=["get"])  # type: ignore[untyped-decorator]
    def links(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """List links (claim/adopt/fork) for this character."""
        character = self.get_object()

        # Links where this character is source or target
        links = CharacterLink.objects.filter(
            models.Q(source=character) | models.Q(target=character)
        ).select_related("source", "target")

        serializer = CharacterLinkSerializer(links, many=True)
        return Response(serializer.data)

    # =================================================================
    # CLAIM / ADOPT / FORK Actions
    # =================================================================

    @action(detail=True, methods=["post"])  # type: ignore[untyped-decorator]
    def claim(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """Propose a Claim: 'Your NPC was my PC all along.'"""
        return self._create_link_request(request, LinkType.CLAIM)

    @action(detail=True, methods=["post"])  # type: ignore[untyped-decorator]
    def adopt(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """Propose an Adoption: 'I want to make this NPC my PC.'"""
        return self._create_link_request(request, LinkType.ADOPT)

    @action(detail=True, methods=["post"])  # type: ignore[untyped-decorator]
    def fork(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """Propose a Fork: 'I want to create a character inspired by this NPC.'"""
        return self._create_link_request(request, LinkType.FORK)

    def _create_link_request(self, request: Request, link_type: str) -> Response:
        target = self.get_object()
        proposed: Character | None = None
        if link_type == LinkType.CLAIM:
            proposed_id = request.data.get("proposed_character")
            if not proposed_id:
                return Response(
                    {"error": "A claim requires an existing PC to propose."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            proposed = Character.objects.filter(id=proposed_id).first()

        try:
            link_request = LinkService.create_request(
                requester=request.user,
                target_character=target,
                link_type=link_type,
                message=request.data.get("message", ""),
                proposed_character=proposed,
            )
        except ValidationError as exc:
            return Response(
                {"error": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LinkRequestViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    API endpoint for link requests (Claim/Adopt/Fork proposals).
    """

    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self) -> QuerySet[LinkRequest]:
        user = self.request.user

        # Show requests user made or received
        return LinkRequest.objects.filter(
            models.Q(requester=user) | models.Q(target_character__creator=user)
        ).select_related("requester", "target_character", "proposed_character")

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action == "create":
            return LinkRequestCreateSerializer
        return LinkRequestSerializer

    @action(detail=True, methods=["post"])  # type: ignore[untyped-decorator]
    def accept(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """
        Accept a link request.

        Only the target character's creator can accept.
        """
        link_request = self.get_object()

        if link_request.target_character.creator != request.user:
            return Response(
                {"error": "Only the character's creator can accept."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            LinkService.accept_request(
                request=link_request,
                response_message=request.data.get("message", ""),
            )
        except ValidationError as exc:
            return Response(
                {"error": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link_request.refresh_from_db()
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])  # type: ignore[untyped-decorator]
    def reject(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """
        Reject a link request.

        Only the target character's creator can reject.
        """
        link_request = self.get_object()

        if link_request.target_character.creator != request.user:
            return Response(
                {"error": "Only the character's creator can reject."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Delegate to the service: it validates the PENDING state, resolves the
        # request, and promotes the next queued request. Never mutate link state
        # here — the queue invariant lives in LinkService (08-characters).
        try:
            LinkService.reject_request(
                link_request, response_message=request.data.get("message", "")
            )
        except ValidationError as exc:
            return Response(
                {"error": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link_request.refresh_from_db()
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])  # type: ignore[untyped-decorator]
    def cancel(self, request: Request, pk: str | None = None, **kwargs: Any) -> Response:
        """
        Cancel a link request.

        Only the requester can cancel.
        """
        link_request = self.get_object()

        if link_request.requester != request.user:
            return Response(
                {"error": "Only the requester can cancel."}, status=status.HTTP_403_FORBIDDEN
            )

        # Delegate to the service. cancel_request accepts both PENDING and QUEUED
        # (a requester may withdraw a request while it waits in the queue) and
        # promotes the next queued request when a PENDING one is cancelled.
        try:
            LinkService.cancel_request(link_request)
        except ValidationError as exc:
            return Response(
                {"error": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link_request.refresh_from_db()
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data)


class FollowViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    API endpoint for follows.
    """

    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self) -> QuerySet[Follow]:
        return Follow.objects.filter(follower=self.request.user).select_related("content_type")

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action == "create":
            from suddenly.core.serializers import FollowCreateSerializer

            return FollowCreateSerializer
        return FollowSerializer

    @action(detail=False, methods=["post"])  # type: ignore[untyped-decorator]
    def toggle(self, request: Request, **kwargs: Any) -> Response:
        """Toggle follow status for a target."""
        target_type = request.data.get("target_type")
        target_id = request.data.get("target_id")

        if not target_type or not target_id:
            return Response(
                {"error": "target_type and target_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Map target_type to content type
        from suddenly.core.utils import content_type_for_actor

        try:
            content_type = content_type_for_actor(target_type)
        except ValueError:
            return Response(
                {"error": f"Invalid target_type: {target_type}"}, status=status.HTTP_400_BAD_REQUEST
            )

        follow = Follow.objects.filter(
            follower=request.user, content_type=content_type, object_id=target_id
        ).first()

        if follow:
            follow.delete()
            return Response({"following": False})

        Follow.objects.create(follower=request.user, content_type=content_type, object_id=target_id)
        return Response({"following": True}, status=status.HTTP_201_CREATED)
