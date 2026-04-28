"""
Custom allauth adapter to force transactional emails to the instance language.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import translation
from allauth.account.adapter import DefaultAccountAdapter


class SuddenlyAccountAdapter(DefaultAccountAdapter):
    """Force all outgoing allauth emails to use the instance LANGUAGE_CODE.

    This ensures signup confirmations, password resets, email confirmations,
    and account deletion emails are always in the instance language regardless
    of the requesting user's interface_language preference.
    """

    def send_mail(self, template_prefix: str, email: str, context: dict[str, Any]) -> None:
        with translation.override(settings.LANGUAGE_CODE):
            super().send_mail(template_prefix, email, context)
