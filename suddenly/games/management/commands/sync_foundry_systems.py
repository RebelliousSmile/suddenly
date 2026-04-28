"""Management command to sync FoundryVTT systems catalog."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Sync FoundryVTT game systems catalog into the GameSystem table."""

    help = "Sync FoundryVTT game systems catalog into GameSystem table."

    def handle(self, *args: Any, **options: Any) -> None:
        from suddenly.games.tasks import sync_foundry_systems

        self.stdout.write("Syncing FoundryVTT systems...")
        result = sync_foundry_systems()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: created={result['created']}"
                f" updated={result['updated']}"
                f" deprecated={result['deprecated']}"
            )
        )
