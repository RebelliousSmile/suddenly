"""
Core service layer — shared business queries used by views.
"""

from __future__ import annotations

from django.db.models import QuerySet

from suddenly.games.models import Report, ReportStatus


def get_recent_public_reports(limit: int = 3) -> QuerySet[Report]:
    return (
        Report.objects.filter(
            status=ReportStatus.PUBLISHED,
            visibility="public",
            remote=False,
        )
        .select_related("author", "game")
        .prefetch_related("cast", "quotes")
        .order_by("-published_at")[:limit]
    )
