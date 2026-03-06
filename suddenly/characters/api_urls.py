"""
Characters API URL patterns.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CharacterViewSet, FollowViewSet, LinkRequestViewSet, QuoteViewSet

router = DefaultRouter()
router.register(r"characters", CharacterViewSet, basename="character")
router.register(r"link-requests", LinkRequestViewSet, basename="link-request")
router.register(r"quotes", QuoteViewSet, basename="quote")
router.register(r"follows", FollowViewSet, basename="follow")

urlpatterns = [
    path("", include(router.urls)),
]
