"""
Remote profile enrichment — parties/personnages/activité (DEC-C5, epic C #133).

Derives a bounded "what has this remote actor been up to" summary from their
outbox, for display on `federation/remote_profile.html`. Every remote fetch
goes through `_http.fetch_ap_json`/`fetch_ap_actor` (SSRF-safe, IP-pinned, no
redirects) — never a raw HTTP client. Every function here is tolerant of a
partial or hostile response: a failed/missing/malformed fetch degrades to an
empty list, never an exception — a caller must never see a 500 because a
remote server sent garbage (DEC-C5).

Games/characters are Suddenly-specific: they're derived from AS2 fields
(`context`, `tag` Mention) that `serialize_report` only populates for local
Reports. A non-Suddenly actor's outbox (e.g. Mastodon Notes) has no such
fields, so `is_suddenly=False` skips that derivation and only "activity" is
populated — matching the plan's Task 2 (résumé + activité récente, no
Suddenly-specific section).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

# Hard bounds (DEC-C5 risk register: "jamais dans une boucle non bornée").
# Remote pagination is not followed past the outbox's first page at MVP.
MAX_OUTBOX_ITEMS = 10
MAX_GAMES = 5
MAX_CHARACTERS = 5

_AP_ACCEPT = "application/activity+json, application/ld+json"


def fetch_remote_actor_collections(
    actor_data: dict[str, Any], *, is_suddenly: bool
) -> dict[str, list[dict[str, Any]]]:
    """Fetch and summarize a remote actor's outbox for profile enrichment.

    Always populates "activity" (bounded, works for any actor — a Suddenly
    Article or a Mastodon Note). "games"/"characters" are populated only when
    `is_suddenly` is True.
    """
    result: dict[str, list[dict[str, Any]]] = {"activity": [], "games": [], "characters": []}

    outbox_url = actor_data.get("outbox")
    if not isinstance(outbox_url, str) or not outbox_url:
        return result

    items = _fetch_outbox_items(outbox_url)
    result["activity"] = [s for s in (_summarize_activity_item(i) for i in items) if s]

    if not is_suddenly:
        return result

    game_iris = _unique_ordered(item.get("context") for item in items if isinstance(item, dict))[
        :MAX_GAMES
    ]
    result["games"] = [s for s in (_fetch_actor_summary(iri) for iri in game_iris) if s]

    result["characters"] = _extract_character_mentions(items)

    return result


def _fetch_outbox_items(
    outbox_url: str, *, max_items: int = MAX_OUTBOX_ITEMS
) -> list[dict[str, Any]]:
    """Fetch up to `max_items` items from an actor's outbox, first page only.

    Tolerates both shapes seen in the wild: `orderedItems` inlined on the root
    `OrderedCollection` (this server's own `user_outbox`), or a separate
    `first` `OrderedCollectionPage` (spec-conformant remote servers). Never
    follows `next` — remote pagination stops at page 1 (DEC-C5).
    """
    from ._http import fetch_ap_json

    data = fetch_ap_json(outbox_url, accept=_AP_ACCEPT)
    if not isinstance(data, dict):
        return []

    items = data.get("orderedItems")
    if not isinstance(items, list):
        first = data.get("first")
        page: dict[str, Any] | None = None
        if isinstance(first, str):
            page = fetch_ap_json(first, accept=_AP_ACCEPT)
        elif isinstance(first, dict):
            page = first
        items = page.get("orderedItems") if isinstance(page, dict) else None

    if not isinstance(items, list):
        return []

    return [i for i in items if isinstance(i, dict)][:max_items]


def _summarize_activity_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Reduce an outbox item to a display summary, unwrapping a `Create` once."""
    if not isinstance(item, dict):
        return None

    if item.get("type") == "Create" and isinstance(item.get("object"), dict):
        item = item["object"]

    if item.get("type") not in ("Article", "Note"):
        return None

    return {
        "title": item.get("name", ""),
        "content": item.get("content") or item.get("summary") or "",
        "url": item.get("url") or item.get("id", ""),
        "published": item.get("published", ""),
    }


def _extract_character_mentions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive unique character mentions from outbox item `tag` (Mention) entries.

    No extra fetch: the Mention already carries a display `name`
    (`serialize_report` emits `@{character.name}`).
    """
    entries: list[dict[str, Any]] = []
    seen_hrefs: set[str] = set()

    for item in items:
        tags = item.get("tag") if isinstance(item, dict) else None
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if not isinstance(tag, dict) or tag.get("type") != "Mention":
                continue
            href = tag.get("href")
            if not isinstance(href, str) or not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            entries.append({"name": tag.get("name") or href, "url": href})
            if len(entries) >= MAX_CHARACTERS:
                return entries

    return entries


def _fetch_actor_summary(iri: str) -> dict[str, Any] | None:
    """Fetch a remote actor doc (Game/Group) and reduce it to a display summary."""
    from ._http import fetch_ap_actor

    data = fetch_ap_actor(iri)
    if not isinstance(data, dict):
        return None

    name = data.get("name") or data.get("preferredUsername") or iri
    return {"name": name, "url": iri, "summary": data.get("summary", "")}


def _unique_ordered(values: Iterable[Any]) -> list[str]:
    """First-seen-order de-duplication of string values, dropping non-strings."""
    seen: set[str] = set()
    result: list[str] = []
    for v in values:
        if isinstance(v, str) and v and v not in seen:
            seen.add(v)
            result.append(v)
    return result
