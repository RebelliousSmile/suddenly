"""Celery tasks for the games app.

`muses_post_ingest` orchestrates the existing Muses analyze features on a
freshly ingested report (#126). It is pure orchestration: no new hub contract,
no new table. Everything degrades cleanly — if the author has not opted in, or
the hub is disabled/unreachable, the task is a no-op and the ingestion result
is untouched (#88).
"""

from __future__ import annotations

import logging

from celery import shared_task

from suddenly.muses.client import Corpus, MusesClient
from suddenly.muses.exceptions import MusesError

logger = logging.getLogger("suddenly.muses")

# Ordered from strongest so notification copy reads fort → faible.
_STRENGTH_LABELS = [("strong", "fort"), ("medium", "moyen"), ("weak", "faible")]


def _report_corpus(report: object) -> Corpus:
    """Flatten a Report and its published rapports into a single labelled corpus.

    The report is resolved *by construction* — it came through the membrane,
    which only lets resolved content across (§5), so nothing live leaks here.
    """
    parts: list[str] = []
    title = getattr(report, "title", "")
    if title:
        parts.append(title)
    content = getattr(report, "content", "")
    if content:
        parts.append(content)
    for rapport in report.rapports.filter(status="published").order_by("order", "created_at"):  # type: ignore[attr-defined]
        if rapport.content:
            parts.append(rapport.content)
    tags = [t.name for t in report.tags.all()]  # type: ignore[attr-defined]
    return Corpus(label="report", content="\n\n".join(parts), tags=tags)


def _links_summary(links: list[dict[str, object]]) -> str:
    """Human summary of federated-link suggestions, classed fort / moyen / faible."""
    counts = {key: 0 for key, _ in _STRENGTH_LABELS}
    for link in links:
        strength = str(link.get("strength", "")).lower()
        if strength in counts:
            counts[strength] += 1
    pieces = [f"{counts[key]} {label}" for key, label in _STRENGTH_LABELS if counts[key]]
    total = sum(counts.values())
    if not total:
        return ""
    detail = ", ".join(pieces)
    return f"Muses a repéré {total} ancrage(s) fédéré(s) possible(s) ({detail})."


@shared_task  # type: ignore[untyped-decorator]
def muses_post_ingest(report_id: str) -> str:
    """After a successful ingestion, offer an editable summary + federated links.

    Gated by ``SUDDENLY_MUSES_ENABLED`` *and* the author's opt-in. Each hub call
    is guarded independently: one failing does not sink the other, and a fully
    unavailable hub simply produces no assistance (no unit debited).
    """
    from django.contrib.contenttypes.models import ContentType

    from suddenly.core.models import Notification, NotificationType
    from suddenly.games.models import Report

    if not MusesClient.is_enabled():
        return "skipped: muses disabled"

    try:
        report = Report.objects.select_related("author").get(id=report_id)
    except Report.DoesNotExist:
        return "skipped: report gone"

    author = report.author
    if author is None or not getattr(author, "muses_post_ingest_optin", False):
        return "skipped: author opted out"

    client = MusesClient()
    corpus = _report_corpus(report)
    notification_bits: list[str] = []

    # 1) Summary (#83) — attached as an editable proposal, never auto-published.
    try:
        result = client.analyze(feature="summary", content=corpus.content, tags=corpus.tags)
        summary = str(result.get("summary", "")).strip()
        if summary:
            report.muses_summary_proposal = summary
            report.save(update_fields=["muses_summary_proposal"])
            notification_bits.append("Un résumé éditable vous est proposé.")
    except MusesError as exc:
        logger.info("Muses summary skipped for report %s: %s", report_id, exc)

    # 2) Federated links (#84) — classified fort / moyen / faible.
    try:
        result = client.analyze(feature="federated_links", content=corpus.content, tags=corpus.tags)
        links = result.get("links") or []
        summary_line = _links_summary(links if isinstance(links, list) else [])
        if summary_line:
            notification_bits.append(summary_line)
    except MusesError as exc:
        logger.info("Muses federated links skipped for report %s: %s", report_id, exc)

    if not notification_bits:
        return "done: no assistance produced"

    Notification.objects.create(
        recipient=author,
        type=NotificationType.MUSES_SUGGESTION,
        target_content_type=ContentType.objects.get_for_model(Report),
        target_object_id=report.id,
        message=" ".join(notification_bits),
    )
    return "done: notified"
