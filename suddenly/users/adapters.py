"""
Custom allauth adapter to force transactional emails to the instance language.
"""

from __future__ import annotations

from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.utils import translation

from suddenly.core.models import InstanceSettings


class SuddenlyAccountAdapter(DefaultAccountAdapter):  # type: ignore[misc]
    """Force all outgoing allauth emails to use the instance language.

    This ensures signup confirmations, password resets, email confirmations,
    and account deletion emails are always in the instance language regardless
    of the requesting user's interface_language preference.

    Registration open/closed state is also driven by ``InstanceSettings`` so
    that the admin panel toggle takes effect without a server restart.
    """

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """Return whether new user registrations are currently accepted."""
        try:
            return InstanceSettings.get().registrations_open
        except Exception:  # noqa: BLE001 — fall back to open if DB unavailable
            return True

    def send_mail(self, template_prefix: str, email: str, context: dict[str, Any]) -> None:
        try:
            lang = InstanceSettings.get().language
        except Exception:  # noqa: BLE001 — fall back to settings if DB unavailable
            lang = settings.LANGUAGE_CODE
        with translation.override(lang):
            super().send_mail(template_prefix, email, context)
