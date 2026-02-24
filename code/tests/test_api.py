"""
Tests for Suddenly API endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from suddenly.characters.models import Character, CharacterStatus, LinkRequest


class TestGameAPI:
    """Tests for Game API endpoints."""
    
    def test_list_games(self, api_client, game):
        response = api_client.get("/api/games/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_create_game_authenticated(self, authenticated_client, user):
        data = {
            "title": "New Game",
            "description": "A new game",
            "game_system": "D&D 5e",
            "is_public": True
        }
        response = authenticated_client.post("/api/games/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New Game"
    
    def test_create_game_unauthenticated(self, api_client):
        data = {"title": "Unauthorized Game"}
        response = api_client.post("/api/games/", data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCharacterAPI:
    """Tests for Character API endpoints."""
    
    def test_list_characters(self, api_client, character):
        response = api_client.get("/api/characters/")
        assert response.status_code == status.HTTP_200_OK
    
    def test_filter_available_characters(self, api_client, character, pc_character):
        response = api_client.get("/api/characters/?available=true")
        assert response.status_code == status.HTTP_200_OK
        
        # Should only return NPCs
        for char in response.data:
            assert char["status"] == "npc"
    
    def test_search_characters(self, api_client, character):
        response = api_client.get("/api/characters/search/?q=Test")
        assert response.status_code == status.HTTP_200_OK
    
    def test_claim_character(self, authenticated_client, user, character, pc_character, game):
        # Create another user's NPC
        other_npc = Character.objects.create(
            name="Other NPC",
            status=CharacterStatus.NPC,
            creator=user,
            origin_game=game
        )
        
        data = {
            "proposed_character": str(pc_character.id),
            "message": "This was my PC!"
        }
        
        response = authenticated_client.post(
            f"/api/characters/{other_npc.id}/claim/",
            data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["type"] == "claim"
    
    def test_adopt_character(self, authenticated_client, character):
        data = {"message": "I want to adopt this NPC"}
        
        response = authenticated_client.post(
            f"/api/characters/{character.id}/adopt/",
            data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["type"] == "adopt"
    
    def test_fork_character(self, authenticated_client, character):
        data = {"message": "Creating a related character"}
        
        response = authenticated_client.post(
            f"/api/characters/{character.id}/fork/",
            data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["type"] == "fork"
    
    def test_cannot_claim_unavailable_character(self, authenticated_client, pc_character):
        data = {"message": "Trying to claim a PC"}
        
        response = authenticated_client.post(
            f"/api/characters/{pc_character.id}/adopt/",
            data
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLinkRequestAPI:
    """Tests for LinkRequest API endpoints."""
    
    @pytest.fixture
    def link_request(self, db, user, other_user, character):
        return LinkRequest.objects.create(
            type="adopt",
            requester=other_user,
            target_character=character,
            message="I want to adopt"
        )
    
    def test_accept_link_request(self, api_client, user, link_request):
        api_client.force_authenticate(user=user)
        
        response = api_client.post(
            f"/api/link-requests/{link_request.id}/accept/",
            {"message": "Approved!"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "accepted"
    
    def test_reject_link_request(self, api_client, user, link_request):
        api_client.force_authenticate(user=user)
        
        response = api_client.post(
            f"/api/link-requests/{link_request.id}/reject/",
            {"message": "Sorry, not now"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "rejected"
    
    def test_only_creator_can_accept(self, api_client, other_user, link_request):
        # other_user is the requester, not the creator
        api_client.force_authenticate(user=other_user)
        
        response = api_client.post(
            f"/api/link-requests/{link_request.id}/accept/"
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestReportAPI:
    """Tests for Report API endpoints."""
    
    def test_create_draft_report(self, authenticated_client, game):
        data = {
            "title": "New Report",
            "content": "Session content here",
            "game": str(game.id)
        }
        
        response = authenticated_client.post("/api/reports/", data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "draft"
    
    def test_publish_report(self, authenticated_client, report):
        response = authenticated_client.post(
            f"/api/reports/{report.id}/publish/"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "published"


class TestWebFinger:
    """Tests for WebFinger endpoint."""
    
    def test_webfinger_user(self, api_client, user):
        response = api_client.get(
            f"/.well-known/webfinger?resource=acct:{user.username}@localhost"
        )
        
        # Should return 200 or appropriate error based on domain config
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


class TestNodeInfo:
    """Tests for NodeInfo endpoints."""
    
    def test_nodeinfo_index(self, api_client):
        response = api_client.get("/.well-known/nodeinfo")
        
        assert response.status_code == status.HTTP_200_OK
        assert "links" in response.data
    
    def test_nodeinfo_2_0(self, api_client):
        response = api_client.get("/.well-known/nodeinfo/2.0")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["software"]["name"] == "suddenly"
        assert "activitypub" in response.data["protocols"]
