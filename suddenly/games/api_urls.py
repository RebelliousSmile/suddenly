"""
Games API URL patterns.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .ingest import IngestReportView
from .views import GameViewSet, ReportViewSet

router = DefaultRouter()
router.register(r"games", GameViewSet, basename="game")
router.register(r"reports", ReportViewSet, basename="report")

urlpatterns = [
    path("reports/ingest/", IngestReportView.as_view(), name="report-ingest"),
    path("", include(router.urls)),
]
