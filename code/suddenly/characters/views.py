"""
Characters API views with Claim/Adopt/Fork logic.
"""

from django.db import models, transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from suddenly.characters.models import (
    Character, CharacterStatus, Quote, CharacterAppearance,
    LinkRequest, LinkRequestStatus, LinkType,
    CharacterLink, SharedSequence, Follow
)
from suddenly.core.serializers import (
    CharacterSerializer, CharacterDetailSerializer, CharacterSearchSerializer,
    QuoteSerializer, QuoteCreateSerializer,
    LinkRequestSerializer, LinkRequestCreateSerializer,
    CharacterLinkSerializer, SharedSequenceSerializer,
    FollowSerializer
)


class CharacterViewSet(viewsets.ModelViewSet):
    """
    API endpoint for characters.
    
    Includes Claim, Adopt, Fork actions.
    """
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
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
    
    def get_serializer_class(self):
        if self.action == "retrieve":
            return CharacterDetailSerializer
        if self.action == "search":
            return CharacterSearchSerializer
        return CharacterSerializer
    
    @action(detail=False, methods=["get"])
    def search(self, request):
        """
        Search characters for @mention autocomplete.
        
        Query params:
        - q: Search query (name)
        - limit: Max results (default 10)
        """
        query = request.query_params.get("q", "")
        limit = int(request.query_params.get("limit", 10))
        
        if len(query) < 2:
            return Response([])
        
        characters = Character.objects.filter(
            name__icontains=query,
            remote=False
        ).select_related("origin_game")[:limit]
        
        serializer = CharacterSearchSerializer(characters, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=["get"])
    def quotes(self, request, pk=None):
        """List public quotes for this character."""
        character = self.get_object()
        quotes = character.quotes.filter(visibility="public")
        serializer = QuoteSerializer(quotes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=["get"])
    def appearances(self, request, pk=None):
        """List reports where this character appears."""
        character = self.get_object()
        appearances = character.appearances.select_related(
            "report", "report__author", "report__game"
        ).filter(report__status="published")
        
        data = [{
            "report_id": a.report.id,
            "report_title": a.report.title,
            "game_title": a.report.game.title,
            "role": a.role,
            "published_at": a.report.published_at
        } for a in appearances]
        
        return Response(data)
    
    @action(detail=True, methods=["get"])
    def links(self, request, pk=None):
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
    
    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        """
        Propose a Claim: "Your NPC was my PC all along."
        
        Required: proposed_character (the existing PC)
        Optional: message (explanation)
        """
        target = self.get_object()
        
        if not target.is_available:
            return Response(
                {"error": "This character is not available for claim."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        proposed_id = request.data.get("proposed_character")
        if not proposed_id:
            return Response(
                {"error": "A claim requires an existing PC to propose."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            proposed = Character.objects.get(
                id=proposed_id,
                owner=request.user,
                status=CharacterStatus.PC
            )
        except Character.DoesNotExist:
            return Response(
                {"error": "Invalid proposed character. Must be your own PC."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        link_request = LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=request.user,
            target_character=target,
            proposed_character=proposed,
            message=request.data.get("message", ""),
            status=LinkRequestStatus.PENDING
        )
        
        # TODO: Send ActivityPub Offer(Claim) activity
        
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["post"])
    def adopt(self, request, pk=None):
        """
        Propose an Adoption: "I want to make this NPC my PC."
        
        Optional: message (explanation)
        """
        target = self.get_object()
        
        if not target.is_available:
            return Response(
                {"error": "This character is not available for adoption."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        link_request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=request.user,
            target_character=target,
            message=request.data.get("message", ""),
            status=LinkRequestStatus.PENDING
        )
        
        # TODO: Send ActivityPub Offer(Adopt) activity
        
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["post"])
    def fork(self, request, pk=None):
        """
        Propose a Fork: "I want to create a character inspired by this NPC."
        
        Required: name (new character name)
        Optional: description, relationship (how they're related)
        """
        target = self.get_object()
        
        if not target.is_available:
            return Response(
                {"error": "This character is not available for fork."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        link_request = LinkRequest.objects.create(
            type=LinkType.FORK,
            requester=request.user,
            target_character=target,
            message=request.data.get("message", ""),
            status=LinkRequestStatus.PENDING
        )
        
        # Store fork details in message for now
        # TODO: Add separate fields for fork character details
        
        # TODO: Send ActivityPub Offer(Fork) activity
        
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LinkRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for link requests (Claim/Adopt/Fork proposals).
    """
    
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    
    def get_queryset(self):
        user = self.request.user
        
        # Show requests user made or received
        return LinkRequest.objects.filter(
            models.Q(requester=user) | 
            models.Q(target_character__creator=user)
        ).select_related(
            "requester", "target_character", "proposed_character"
        )
    
    def get_serializer_class(self):
        if self.action == "create":
            return LinkRequestCreateSerializer
        return LinkRequestSerializer
    
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """
        Accept a link request.
        
        Only the target character's creator can accept.
        """
        link_request = self.get_object()
        
        if link_request.target_character.creator != request.user:
            return Response(
                {"error": "Only the character's creator can accept."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if link_request.status != LinkRequestStatus.PENDING:
            return Response(
                {"error": "This request is no longer pending."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Update request status
            link_request.status = LinkRequestStatus.ACCEPTED
            link_request.resolved_at = timezone.now()
            link_request.response_message = request.data.get("message", "")
            link_request.save()
            
            target = link_request.target_character
            
            # Process based on type
            if link_request.type == LinkType.CLAIM:
                # Claim: PC "was" the NPC all along
                source = link_request.proposed_character
                target.status = CharacterStatus.CLAIMED
                target.save()
                
            elif link_request.type == LinkType.ADOPT:
                # Adopt: NPC becomes requester's PC
                source = target  # Same character, new owner
                target.status = CharacterStatus.ADOPTED
                target.owner = link_request.requester
                target.save()
                
            elif link_request.type == LinkType.FORK:
                # Fork: Create new character derived from NPC
                source = Character.objects.create(
                    name=request.data.get("fork_name", f"{target.name} (fork)"),
                    description=request.data.get("fork_description", ""),
                    status=CharacterStatus.PC,
                    owner=link_request.requester,
                    creator=link_request.requester,
                    origin_game=target.origin_game,
                    parent=target
                )
                target.status = CharacterStatus.FORKED
                target.save()
            
            # Create the established link
            character_link = CharacterLink.objects.create(
                type=link_request.type,
                source=source,
                target=target,
                link_request=link_request,
                description=request.data.get("link_description", "")
            )
            
            # Create empty shared sequence for collaboration
            SharedSequence.objects.create(
                link=character_link,
                status="draft"
            )
            
            # TODO: Send ActivityPub Accept(Offer) activity
        
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """
        Reject a link request.
        
        Only the target character's creator can reject.
        """
        link_request = self.get_object()
        
        if link_request.target_character.creator != request.user:
            return Response(
                {"error": "Only the character's creator can reject."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if link_request.status != LinkRequestStatus.PENDING:
            return Response(
                {"error": "This request is no longer pending."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        link_request.status = LinkRequestStatus.REJECTED
        link_request.resolved_at = timezone.now()
        link_request.response_message = request.data.get("message", "")
        link_request.save()
        
        # TODO: Send ActivityPub Reject(Offer) activity
        
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancel a link request.
        
        Only the requester can cancel.
        """
        link_request = self.get_object()
        
        if link_request.requester != request.user:
            return Response(
                {"error": "Only the requester can cancel."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if link_request.status != LinkRequestStatus.PENDING:
            return Response(
                {"error": "This request is no longer pending."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        link_request.status = LinkRequestStatus.CANCELLED
        link_request.resolved_at = timezone.now()
        link_request.save()
        
        serializer = LinkRequestSerializer(link_request)
        return Response(serializer.data)


class QuoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint for quotes.
    """
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Quote.objects.filter(remote=False)
        
        if self.request.user.is_authenticated:
            # Include user's private quotes
            return queryset.filter(
                models.Q(visibility="public") | 
                models.Q(author=self.request.user)
            ).select_related("character", "author")
        
        return queryset.filter(visibility="public").select_related("character", "author")
    
    def get_serializer_class(self):
        if self.action == "create":
            return QuoteCreateSerializer
        return QuoteSerializer


class FollowViewSet(viewsets.ModelViewSet):
    """
    API endpoint for follows.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    
    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user).select_related('content_type')
    
    def get_serializer_class(self):
        if self.action == 'create':
            from suddenly.core.serializers import FollowCreateSerializer
            return FollowCreateSerializer
        return FollowSerializer
    
    @action(detail=False, methods=["post"])
    def toggle(self, request):
        """Toggle follow status for a target."""
        from django.contrib.contenttypes.models import ContentType
        
        target_type = request.data.get("target_type")
        target_id = request.data.get("target_id")
        
        if not target_type or not target_id:
            return Response(
                {"error": "target_type and target_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Map target_type to content type
        model_map = {
            "user": ("users", "user"),
            "character": ("characters", "character"),
            "game": ("games", "game"),
        }
        
        if target_type not in model_map:
            return Response(
                {"error": f"Invalid target_type: {target_type}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        app_label, model = model_map[target_type]
        content_type = ContentType.objects.get(app_label=app_label, model=model)
        
        follow = Follow.objects.filter(
            follower=request.user,
            content_type=content_type,
            object_id=target_id
        ).first()
        
        if follow:
            follow.delete()
            return Response({"following": False})
        
        Follow.objects.create(
            follower=request.user,
            content_type=content_type,
            object_id=target_id
        )
        return Response({"following": True}, status=status.HTTP_201_CREATED)
