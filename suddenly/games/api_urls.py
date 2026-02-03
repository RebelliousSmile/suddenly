"""
Games API URL patterns.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import GameViewSet, ReportViewSet

router = DefaultRouter()
router.register(r"games", GameViewSet, basename="game")
router.register(r"reports", ReportViewSet, basename="report")

urlpatterns = [
    path("", include(router.urls)),
]
