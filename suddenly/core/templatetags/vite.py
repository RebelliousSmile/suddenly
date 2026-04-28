"""
Template tags for Vite manifest integration.

Reads the Vite build manifest to resolve hashed asset filenames,
enabling proper cache-busting in production.

Usage in templates:
    {% load vite %}
    {% vite_asset "css/main.css" %}  ->  <link rel="stylesheet" href="/static/dist/css/main.css">
    {% vite_asset "js/main.js" %}    ->  <script type="module" src="..."></script>
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)

register = template.Library()

_manifest_cache: dict[str, Any] | None = None


def _load_manifest() -> dict[str, Any]:
    """Load and cache the Vite manifest.json."""
    global _manifest_cache  # noqa: PLW0603 — intentional module-level cache

    if _manifest_cache is not None and not settings.DEBUG:
        return _manifest_cache

    manifest_path = Path(settings.BASE_DIR) / "static" / "dist" / ".vite" / "manifest.json"
    if not manifest_path.exists():
        # Fallback: try legacy manifest location
        manifest_path = Path(settings.BASE_DIR) / "static" / "dist" / "manifest.json"

    if not manifest_path.exists():
        if not settings.DEBUG:
            logger.warning("Vite manifest not found — static assets may be broken")
        return {}

    try:
        with open(manifest_path) as f:
            _manifest_cache = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load Vite manifest: %s", exc)
        return {}

    return _manifest_cache


def _resolve_asset(entry: str) -> str:
    """Resolve an entry name to its hashed filename via the manifest."""
    manifest = _load_manifest()

    # Try exact match first
    if entry in manifest:
        return str(manifest[entry].get("file", entry))

    # Try with src/ prefix (Vite uses src/main.js as key)
    src_entry = f"src/{entry}"
    if src_entry in manifest:
        return str(manifest[src_entry].get("file", entry))

    # No manifest or entry not found — use the entry as-is
    return entry


@register.simple_tag
def vite_asset(entry: str) -> str:
    """Render a <link> or <script> tag for a Vite-built asset.

    In DEBUG mode without a manifest, uses predictable dev paths.
    In production, reads the manifest for hashed filenames.
    """
    resolved = _resolve_asset(entry)
    url = static(f"dist/{resolved}")

    if entry.endswith(".css"):
        return mark_safe(f'<link rel="stylesheet" href="{url}">')
    if entry.endswith(".js"):
        return mark_safe(f'<script type="module" src="{url}"></script>')

    return mark_safe(url)


@register.simple_tag
def vite_css(entry: str = "src/main.js") -> str:
    """Render <link> tags for CSS files associated with a JS entry."""
    manifest = _load_manifest()
    tags: list[str] = []

    if entry in manifest:
        for css_file in manifest[entry].get("css", []):
            url = static(f"dist/{css_file}")
            tags.append(f'<link rel="stylesheet" href="{url}">')

    if not tags:
        # Fallback: assume main.css exists at the predictable path
        url = static("dist/css/main.css")
        tags.append(f'<link rel="stylesheet" href="{url}">')

    return mark_safe("\n    ".join(tags))
