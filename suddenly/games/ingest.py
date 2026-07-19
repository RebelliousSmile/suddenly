"""
Ingestion endpoint for compte rendu blobs exported from choix-narratifs.

POST /api/reports/ingest/
Authorization: X-Ingest-Token <INGEST_TOKEN>

Receives a resolved blob (secrets already revealed, discovery lived),
creates a published Report, and lets the AP signal broadcast it.
"""

from __future__ import annotations

import hmac

from django.conf import settings
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from suddenly.games.models import (
    CastRole,
    Game,
    Rapport,
    RapportKind,
    RapportStatus,
    Report,
    ReportCast,
    ReportStatus,
    ReportVisibility,
)

# ---------------------------------------------------------------------------
# Blob schema (T1)
# ---------------------------------------------------------------------------


class _CastItemSerializer(serializers.Serializer):  # type: ignore[misc]
    character_name = serializers.CharField(max_length=100)
    character_description = serializers.CharField(allow_blank=True, default="")
    role = serializers.ChoiceField(choices=CastRole.choices, default=CastRole.MENTIONED)


class _RapportItemSerializer(serializers.Serializer):  # type: ignore[misc]
    kind = serializers.ChoiceField(
        choices=[
            RapportKind.DESCRIPTION,
            RapportKind.ACTION,
            RapportKind.NARRATION,
        ],
        help_text="DISCUSSION is excluded: it requires a local Character actor.",
    )
    content = serializers.CharField()


class _ReportPayloadSerializer(serializers.Serializer):  # type: ignore[misc]
    title = serializers.CharField(max_length=200, allow_blank=True, default="")
    content = serializers.CharField(allow_blank=True, default="")
    content_warning = serializers.CharField(allow_blank=True, default="")
    session_date = serializers.DateField(required=False, allow_null=True)
    language = serializers.CharField(max_length=10, default="fr")
    visibility = serializers.ChoiceField(
        choices=ReportVisibility.choices, default=ReportVisibility.PUBLIC
    )
    resolved = serializers.BooleanField(
        help_text="Must be true — affirms that the discovery has been lived (§5 guard)."
    )

    def validate_resolved(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("Report must be resolved before export (§5 guard).")
        return value


class ReportIngestSerializer(serializers.Serializer):  # type: ignore[misc]
    schema_version = serializers.CharField(default="1.0")
    game_id = serializers.UUIDField(
        help_text="UUID of the local Suddenly Game this report belongs to."
    )
    report = _ReportPayloadSerializer()
    cast = _CastItemSerializer(many=True, required=False, default=list)
    rapports = _RapportItemSerializer(many=True, required=False, default=list)


# ---------------------------------------------------------------------------
# View (T2)
# ---------------------------------------------------------------------------


class IngestReportView(APIView):  # type: ignore[misc]
    """
    Receive a resolved compte rendu blob from choix-narratifs and publish it.

    Authentication: X-Ingest-Token header checked against settings.INGEST_TOKEN.
    On success: creates a published Report (AP broadcast fires via signal).
    """

    permission_classes = [AllowAny]

    def _check_token(self, request: Request) -> bool:
        expected = getattr(settings, "INGEST_TOKEN", "")
        if not expected:
            return False
        provided = request.headers.get("X-Ingest-Token", "")
        # Constant-time compare to avoid leaking the shared secret via timing.
        return hmac.compare_digest(provided, expected)

    def post(self, request: Request) -> Response:
        if not self._check_token(request):
            return Response(
                {"detail": "Invalid or missing X-Ingest-Token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = ReportIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        payload = data["report"]

        try:
            game = Game.objects.select_related("owner").get(id=data["game_id"], remote=False)
        except Game.DoesNotExist:
            return Response(
                {"detail": "Game not found or not local."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Atomic: the report and its cast/rapports must commit together, or not
        # at all. Combined with the report_post_save signal's transaction.on_commit,
        # the AP Create broadcast only fires once all children exist — never on a
        # half-populated report (03-django-services + ap-pivots §3).
        with transaction.atomic():
            report = Report.objects.create(
                game=game,
                author=game.owner,
                title=payload["title"],
                content=payload["content"],
                content_warning=payload.get("content_warning", ""),
                language=payload.get("language", "fr"),
                visibility=payload.get("visibility", ReportVisibility.PUBLIC),
                session_date=payload.get("session_date"),
                status=ReportStatus.PUBLISHED,
                # published_at is set automatically by the pre_save signal
            )

            ReportCast.objects.bulk_create(
                [
                    ReportCast(
                        report=report,
                        new_character_name=cast_item["character_name"],
                        new_character_description=cast_item.get("character_description", ""),
                        role=cast_item.get("role", CastRole.MENTIONED),
                    )
                    for cast_item in data.get("cast", [])
                ]
            )

            for rapport_item in data.get("rapports", []):
                Rapport.objects.create(
                    report=report,
                    kind=rapport_item["kind"],
                    content=rapport_item["content"],
                    status=RapportStatus.PUBLISHED,
                )

        # Re-open a social Offer on the imported scene, addressed to the
        # author's followers (Epic B, #132 — replaces the retired Muses hook).
        from suddenly.offers.models import OfferKind
        from suddenly.offers.services import OfferService

        OfferService.open_offer(kind=OfferKind.SUMMARY, carrier=report, emitter=report.author)

        report_url = f"{settings.AP_BASE_URL}/reports/{report.id}"

        return Response(
            {"id": str(report.id), "url": report_url},
            status=status.HTTP_201_CREATED,
        )
