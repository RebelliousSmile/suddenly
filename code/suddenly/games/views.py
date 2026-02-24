"""
Games API views.
"""

from django.db import models
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from suddenly.games.models import Game, Report, ReportCast
from suddenly.characters.models import Character, CharacterAppearance
from suddenly.core.serializers import (
    GameSerializer, GameCreateSerializer,
    ReportSerializer, ReportCreateSerializer,
    ReportCastSerializer, CharacterSerializer
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Only owners can modify, anyone can read."""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class GameViewSet(viewsets.ModelViewSet):
    """
    API endpoint for games.
    
    list: List all public games
    create: Create a new game
    retrieve: Get game details
    update/partial_update: Update game (owner only)
    delete: Delete game (owner only)
    """
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        queryset = Game.objects.filter(remote=False)
        
        if self.request.user.is_authenticated:
            # Include user's private games
            return queryset.filter(
                models.Q(is_public=True) | models.Q(owner=self.request.user)
            ).select_related("owner")
        
        return queryset.filter(is_public=True).select_related("owner")
    
    def get_serializer_class(self):
        if self.action == "create":
            return GameCreateSerializer
        return GameSerializer
    
    @action(detail=True, methods=["get"])
    def reports(self, request, pk=None):
        """List published reports for this game."""
        game = self.get_object()
        reports = game.reports.filter(status="published").select_related("author")
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=["get"])
    def characters(self, request, pk=None):
        """List characters from this game."""
        game = self.get_object()
        characters = game.characters.all().select_related("owner", "creator")
        serializer = CharacterSerializer(characters, many=True)
        return Response(serializer.data)


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Only authors can modify, anyone can read published."""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.status == "published" or obj.author == request.user
        return obj.author == request.user


class ReportViewSet(viewsets.ModelViewSet):
    """
    API endpoint for reports.
    """
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    
    def get_queryset(self):
        queryset = Report.objects.filter(remote=False)
        
        if self.request.user.is_authenticated:
            # Include user's drafts
            from django.db import models
            return queryset.filter(
                models.Q(status="published") | models.Q(author=self.request.user)
            ).select_related("author", "game")
        
        return queryset.filter(status="published").select_related("author", "game")
    
    def get_serializer_class(self):
        if self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer
    
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
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
                {"error": "Only the author can publish"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if report.status == "published":
            return Response(
                {"error": "Report is already published"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process cast entries
        for cast_entry in report.cast.all():
            character = cast_entry.character
            
            # Create new NPC if needed
            if cast_entry.is_new_character():
                character = Character.objects.create(
                    name=cast_entry.new_character_name,
                    description=cast_entry.new_character_description,
                    status="npc",
                    creator=request.user,
                    origin_game=report.game
                )
            
            # Create appearance
            if character:
                CharacterAppearance.objects.get_or_create(
                    character=character,
                    report=report,
                    defaults={"role": cast_entry.role}
                )
        
        # Publish
        report.status = "published"
        report.published_at = timezone.now()
        report.save()
        
        # TODO: Send ActivityPub Create(Note) activity
        
        serializer = ReportSerializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=["get", "post"])
    def cast(self, request, pk=None):
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
                {"error": "Only the author can modify cast"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReportCastSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(report=report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
