"""Celery tasks for the users app."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task  # type: ignore[untyped-decorator]
def import_follows_from_rows(user_id: str, addresses: list[str]) -> dict[str, int]:
    """Resolve a batch of ``@user@instance`` addresses and create Follows off-request.

    Runs outside the web request so a large CSV cannot tie up a web worker with N
    sequential (blocking) WebFinger calls. Each address is resolved via the
    SSRF-safe path in ``_resolve_and_follow``. Idempotent: ``get_or_create`` on
    Follow makes re-runs no-ops. Returns counts for observability.
    """
    from suddenly.users.models import User
    from suddenly.users.settings_views import _resolve_and_follow

    try:
        follower = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("import_follows_from_rows: user %s not found", user_id)
        return {"imported": 0, "errors": 0}

    imported = 0
    errors = 0
    for address in addresses:
        if _resolve_and_follow(follower, address):
            imported += 1
        else:
            errors += 1

    logger.info(
        "import_follows_from_rows: user=%s imported=%d errors=%d",
        user_id,
        imported,
        errors,
    )
    return {"imported": imported, "errors": errors}
