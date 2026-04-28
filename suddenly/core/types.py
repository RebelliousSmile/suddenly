"""Typed request classes for authenticated views."""

from __future__ import annotations

from django.http import HttpRequest

from suddenly.users.models import User


class AuthenticatedRequest(HttpRequest):
    user: User
