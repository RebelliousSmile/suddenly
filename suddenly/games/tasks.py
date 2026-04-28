"""Celery tasks for games app."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from celery import shared_task

logger = logging.getLogger(__name__)

_FOUNDRY_SYSTEMS_URL = "https://foundryvtt.com/packages/systems/"
_USER_AGENT = "Suddenly/1.0 (contact@suddenly.social)"


@shared_task(bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def sync_foundry_systems(self: Any) -> dict[str, int]:
    """Scrape FoundryVTT systems catalog and upsert into GameSystem table."""
    from .models import GameSystem

    headers = {"User-Agent": _USER_AGENT}
    systems: dict[str, str] = {}  # slug -> name

    try:
        with httpx.Client(headers=headers, timeout=15) as client:
            resp = client.get(_FOUNDRY_SYSTEMS_URL)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            total_pages = _parse_total_pages(soup)
            systems.update(_extract_systems(soup))

            for page in range(2, total_pages + 1):
                resp = client.get(f"{_FOUNDRY_SYSTEMS_URL}?page={page}")
                resp.raise_for_status()
                systems.update(_extract_systems(BeautifulSoup(resp.text, "html.parser")))

    except Exception as exc:
        logger.error("sync_foundry_systems scrape failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)

    now = datetime.now(tz=UTC)
    created = updated = 0
    seen_slugs: set[str] = set()

    for slug, name in systems.items():
        seen_slugs.add(slug)
        _, was_created = GameSystem.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "is_deprecated": False, "synced_at": now},
        )
        if was_created:
            created += 1
        else:
            updated += 1

    deprecated = (
        GameSystem.objects.exclude(slug__in=seen_slugs)
        .filter(is_deprecated=False)
        .update(is_deprecated=True)
    )

    logger.info(
        "sync_foundry_systems: created=%d updated=%d deprecated=%d",
        created,
        updated,
        deprecated,
    )
    return {"created": created, "updated": updated, "deprecated": deprecated}


def _parse_total_pages(soup: BeautifulSoup) -> int:
    """Extract total page count from pagination text like 'Page 1 of 10'."""
    text = soup.get_text()
    match = re.search(r"Page\s+\d+\s+of\s+(\d+)", text)
    return int(match.group(1)) if match else 1


def _extract_systems(soup: BeautifulSoup) -> dict[str, str]:
    """Extract {slug: name} from a FoundryVTT systems listing page."""
    systems: dict[str, str] = {}
    for a in soup.select("a[href^='/packages/']"):
        href = str(a.get("href", ""))
        parts = href.strip("/").split("/")
        # href format: /packages/{slug}
        if len(parts) == 2 and parts[0] == "packages":
            slug = parts[1]
            name = a.get_text(strip=True)
            if slug and name:
                systems[slug] = name
    return systems
