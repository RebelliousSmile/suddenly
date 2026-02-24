"""
API Serializers for Suddenly.
"""

from rest_framework import serializers

from suddenly.users.models import User
from suddenly.games.models import Game, Report, ReportCast
from suddenly.characters.models import (
    Character, Quote, CharacterAppearance,
    LinkRequest, CharacterLink, SharedSequence, Follow
)


# =================================================================
# User Serializers
# =================================================================

class UserSerializer(serializers.ModelSerializer):
    """Public user representation."""
    
    class Meta:
        model = User
        fields = [
            "id", "username", "display_name", "bio", "avatar",
            "actor_url", "created_at"
        ]
        read_only_fields = fields


class UserDetailSerializer(UserSerializer):
    """Detailed user representation with stats."""
    
    games_count = serializers.SerializerMethodField()
    characters_count = serializers.SerializerMethodField()
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["games_count", "characters_count"]
    
    def get_games_count(self, obj):
        return obj.games.filter(is_public=True).count()
    
    def get_characters_count(self, obj):
        return obj.owned_characters.count()


# =================================================================
# Game Serializers
# =================================================================

class GameSerializer(serializers.ModelSerializer):
    """Game list representation."""
    
    owner = UserSerializer(read_only=True)
    reports_count = serializers.SerializerMethodField()
    characters_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = [
            "id", "title", "description", "game_system", "owner",
            "is_public", "actor_url", "reports_count", "characters_count",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "owner", "actor_url", "created_at", "updated_at"]
    
    def get_reports_count(self, obj):
        return obj.reports.filter(status="published").count()
    
    def get_characters_count(self, obj):
        return obj.characters.count()


class GameCreateSerializer(serializers.ModelSerializer):
    """Game creation."""
    
    class Meta:
        model = Game
        fields = ["title", "description", "game_system", "is_public"]
    
    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


# =================================================================
# Character Serializers
# =================================================================

class CharacterSerializer(serializers.ModelSerializer):
    """Character list representation."""
    
    owner = UserSerializer(read_only=True)
    creator = UserSerializer(read_only=True)
    origin_game_title = serializers.CharField(source="origin_game.title", read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Character
        fields = [
            "id", "name", "description", "avatar", "status",
            "owner", "creator", "origin_game", "origin_game_title",
            "parent", "sheet_url", "is_available", "actor_url",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "owner", "creator", "status", "actor_url",
            "created_at", "updated_at"
        ]


class CharacterDetailSerializer(CharacterSerializer):
    """Detailed character with appearances and quotes."""
    
    appearances_count = serializers.SerializerMethodField()
    quotes_count = serializers.SerializerMethodField()
    forks_count = serializers.SerializerMethodField()
    
    class Meta(CharacterSerializer.Meta):
        fields = CharacterSerializer.Meta.fields + [
            "appearances_count", "quotes_count", "forks_count"
        ]
    
    def get_appearances_count(self, obj):
        return obj.appearances.count()
    
    def get_quotes_count(self, obj):
        return obj.quotes.filter(visibility="public").count()
    
    def get_forks_count(self, obj):
        return obj.forks.count()


class CharacterSearchSerializer(serializers.ModelSerializer):
    """Minimal character for search/autocomplete."""
    
    game_title = serializers.CharField(source="origin_game.title", read_only=True)
    
    class Meta:
        model = Character
        fields = ["id", "name", "avatar", "game_title"]


# =================================================================
# Report Serializers
# =================================================================

class ReportSerializer(serializers.ModelSerializer):
    """Report list representation."""
    
    author = UserSerializer(read_only=True)
    game_title = serializers.CharField(source="game.title", read_only=True)
    characters_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            "id", "title", "content", "game", "game_title", "author",
            "status", "published_at", "characters_count",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "author", "status", "published_at",
            "created_at", "updated_at"
        ]
    
    def get_characters_count(self, obj):
        return obj.character_appearances.count()


class ReportCreateSerializer(serializers.ModelSerializer):
    """Report creation."""
    
    class Meta:
        model = Report
        fields = ["title", "content", "game"]
    
    def validate_game(self, value):
        user = self.context["request"].user
        if value.owner != user:
            raise serializers.ValidationError("You can only add reports to your own games.")
        return value
    
    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        validated_data["status"] = "draft"
        return super().create(validated_data)


class ReportCastSerializer(serializers.ModelSerializer):
    """Cast entry for a report."""
    
    character = CharacterSerializer(read_only=True)
    
    class Meta:
        model = ReportCast
        fields = [
            "id", "report", "character",
            "new_character_name", "new_character_description",
            "role", "created_at"
        ]


# =================================================================
# Quote Serializers
# =================================================================

class QuoteSerializer(serializers.ModelSerializer):
    """Quote representation."""
    
    character = CharacterSerializer(read_only=True)
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = Quote
        fields = [
            "id", "content", "context", "character", "report",
            "visibility", "author", "created_at"
        ]
        read_only_fields = ["id", "author", "created_at"]


class QuoteCreateSerializer(serializers.ModelSerializer):
    """Quote creation."""
    
    class Meta:
        model = Quote
        fields = ["content", "context", "character", "report", "visibility"]
    
    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)


# =================================================================
# Link Serializers
# =================================================================

class LinkRequestSerializer(serializers.ModelSerializer):
    """Link request representation."""
    
    requester = UserSerializer(read_only=True)
    target_character = CharacterSerializer(read_only=True)
    proposed_character = CharacterSerializer(read_only=True)
    
    class Meta:
        model = LinkRequest
        fields = [
            "id", "type", "requester", "target_character",
            "proposed_character", "status", "message",
            "response_message", "created_at", "resolved_at"
        ]
        read_only_fields = [
            "id", "requester", "status", "response_message",
            "created_at", "resolved_at"
        ]


class LinkRequestCreateSerializer(serializers.ModelSerializer):
    """Link request creation."""
    
    class Meta:
        model = LinkRequest
        fields = ["type", "target_character", "proposed_character", "message"]
    
    def validate_target_character(self, value):
        if not value.is_available:
            raise serializers.ValidationError(
                "This character is not available for claim/adopt/fork."
            )
        return value
    
    def validate(self, data):
        if data["type"] == "claim" and not data.get("proposed_character"):
            raise serializers.ValidationError({
                "proposed_character": "A claim requires an existing PC to propose."
            })
        return data
    
    def create(self, validated_data):
        validated_data["requester"] = self.context["request"].user
        validated_data["status"] = "pending"
        return super().create(validated_data)


class CharacterLinkSerializer(serializers.ModelSerializer):
    """Established character link."""
    
    source = CharacterSerializer(read_only=True)
    target = CharacterSerializer(read_only=True)
    
    class Meta:
        model = CharacterLink
        fields = [
            "id", "type", "source", "target",
            "description", "created_at"
        ]


class SharedSequenceSerializer(serializers.ModelSerializer):
    """Shared sequence content."""
    
    class Meta:
        model = SharedSequence
        fields = ["id", "link", "title", "content", "status", "created_at"]
        read_only_fields = ["id", "link", "created_at"]


# =================================================================
# Follow Serializer
# =================================================================

class FollowSerializer(serializers.ModelSerializer):
    """Follow relationship with generic target."""
    
    target_type = serializers.CharField(source='content_type.model', read_only=True)
    target_id = serializers.UUIDField(source='object_id')
    
    class Meta:
        model = Follow
        fields = ["id", "follower", "target_type", "target_id", "created_at"]
        read_only_fields = ["id", "follower", "created_at"]


class FollowCreateSerializer(serializers.Serializer):
    """Create a follow relationship."""
    
    target_type = serializers.ChoiceField(choices=["user", "character", "game"])
    target_id = serializers.UUIDField()
    
    def validate(self, data):
        from django.contrib.contenttypes.models import ContentType
        
        model_map = {
            "user": "users.user",
            "character": "characters.character",
            "game": "games.game",
        }
        
        app_label, model = model_map[data["target_type"]].split(".")
        
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError(f"Invalid target type: {data['target_type']}")
        
        # Check target exists
        model_class = content_type.model_class()
        if not model_class.objects.filter(id=data["target_id"]).exists():
            raise serializers.ValidationError(f"Target {data['target_type']} not found")
        
        data["content_type"] = content_type
        return data
    
    def create(self, validated_data):
        return Follow.objects.create(
            follower=self.context["request"].user,
            content_type=validated_data["content_type"],
            object_id=validated_data["target_id"],
        )
