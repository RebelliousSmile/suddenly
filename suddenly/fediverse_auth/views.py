"""
Views implementing the "Se connecter avec le Fediverse" OAuth flow.

Routes (mounted under ``/accounts/fediverse/``):

- ``login``    GET shows the instance-entry form; POST starts the OAuth dance.
- ``callback`` the instance redirects back here with ``code`` + ``state``.
"""

from __future__ import annotations

import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from suddenly.core.models import InstanceSettings

from . import client, services
from .models import FediverseApp

logger = logging.getLogger(__name__)

_SESSION_KEY = "fediverse_oauth"
_MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _enabled() -> bool:
    return bool(getattr(settings, "FEDIVERSE_LOGIN_ENABLED", True))


def _callback_url() -> str:
    """Absolute callback URL, derived from the stable public base URL.

    Must be byte-for-byte identical at registration, authorize and token time,
    so it is computed from ``AP_BASE_URL`` rather than the incoming request host.
    """
    base = getattr(settings, "AP_BASE_URL", "").rstrip("/")
    return f"{base}{reverse('fediverse_auth:callback')}"


def _safe_next(request: HttpRequest, raw: str | None) -> str:
    if raw and url_has_allowed_host_and_scheme(
        raw, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return raw
    return settings.LOGIN_REDIRECT_URL


@require_http_methods(["GET", "POST"])
def login(request: HttpRequest) -> HttpResponse:
    """Show the instance form (GET) or start the OAuth flow (POST)."""
    if not _enabled():
        raise Http404

    next_url = _safe_next(request, request.GET.get("next") or request.POST.get("next"))

    if request.method == "GET":
        return render(
            request,
            "fediverse_auth/login.html",
            {"next": request.GET.get("next", "")},
        )

    try:
        instance = services.normalize_instance(request.POST.get("instance", ""))
    except services.InvalidInstanceError:
        messages.error(request, _("Invalid instance address. Example: mastodon.social"))
        return render(
            request,
            "fediverse_auth/login.html",
            {"next": request.POST.get("next", ""), "instance": request.POST.get("instance", "")},
            status=400,
        )

    try:
        app = services.get_or_register_app(instance, _callback_url())
    except client.FediverseClientError as exc:
        logger.info("Fediverse app registration failed for %s: %s", instance, exc)
        messages.error(
            request,
            _("Could not connect to %(instance)s. Check the address and try again.")
            % {"instance": instance},
        )
        return render(
            request,
            "fediverse_auth/login.html",
            {"next": request.POST.get("next", ""), "instance": instance},
            status=502,
        )

    state = secrets.token_urlsafe(32)
    request.session[_SESSION_KEY] = {
        "state": state,
        "instance": instance,
        "next": next_url,
        # "connect" when a logged-in user is linking another identity.
        "action": "connect" if request.user.is_authenticated else "login",
    }
    return redirect(client.build_authorize_url(instance, app.client_id, _callback_url(), state))


@require_http_methods(["GET"])
def callback(request: HttpRequest) -> HttpResponse:
    """Handle the redirect back from the instance."""
    if not _enabled():
        raise Http404

    flow = request.session.pop(_SESSION_KEY, None)
    if not flow:
        messages.error(request, _("Sign-in session expired. Please try again."))
        return redirect("account_login")

    # CSRF: the state we generated must match the one echoed back.
    if not request.GET.get("state") or request.GET.get("state") != flow.get("state"):
        messages.error(request, _("Security check failed. Please try again."))
        return redirect("account_login")

    if request.GET.get("error"):
        messages.error(request, _("Sign-in cancelled."))
        return redirect("account_login")

    code = request.GET.get("code")
    instance = flow["instance"]
    if not code:
        messages.error(request, _("Invalid response from the instance. Please try again."))
        return redirect("account_login")

    try:
        app = FediverseApp.objects.get(instance=instance)
        access_token = client.exchange_code(
            instance, app.client_id, app.client_secret, code, _callback_url()
        )
        account = client.verify_credentials(instance, access_token)
    except (FediverseApp.DoesNotExist, client.FediverseClientError) as exc:
        logger.info("Fediverse callback failed for %s: %s", instance, exc)
        messages.error(request, _("Fediverse sign-in failed. Please try again."))
        return redirect("account_login")

    if not account.get("id"):
        messages.error(request, _("The instance did not return a valid account."))
        return redirect("account_login")

    # Connect flow: attach the identity to the already-authenticated user.
    if flow.get("action") == "connect" and request.user.is_authenticated:
        services.link_existing_user(request.user, instance, account)
        messages.success(
            request,
            _("Account @%(acct)s linked successfully.")
            % {"acct": services._handle(account, instance)},
        )
        return redirect(flow["next"])

    try:
        registrations_open = InstanceSettings.get().registrations_open
    except Exception:  # noqa: BLE001 — default open if DB/settings unavailable
        registrations_open = True

    try:
        user, created = services.resolve_or_create_user(
            instance, account, registrations_open=registrations_open
        )
    except PermissionError:
        messages.error(request, _("Registrations are currently closed on this instance."))
        return redirect("account_login")

    auth_login(request, user, backend=_MODEL_BACKEND)
    if created:
        messages.success(request, _("Welcome! Your account was created via the Fediverse."))
    return redirect(flow["next"])
