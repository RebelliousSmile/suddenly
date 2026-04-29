"""Custom decorators for the Suddenly project."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


def admin_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Restrict a view to authenticated instance administrators.

    Checks both ``is_authenticated`` and ``is_admin`` on the request user.
    Non-admin users are redirected to the login URL, matching the behaviour
    of Django's own ``@login_required``.
    """

    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if request.user.is_authenticated and getattr(request.user, "is_admin", False):
            return view_func(request, *args, **kwargs)
        login_url: str = getattr(settings, "LOGIN_URL", "/accounts/login/")
        return redirect(login_url)

    return _wrapped_view
