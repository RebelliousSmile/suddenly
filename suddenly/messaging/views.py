"""
Front-end HTMX views for federated direct messages (Epic E, #135, DEC-E7).

Inbox (conversation list + unread), thread (mark_read on open), composer
(pre-filled via ``?to=<uuid>``), send (mutuality-gated, DEC-E2). Mirrors the
``characters``/``games`` front-view conventions: ``htmx_render`` for
full-page-vs-fragment, ``getattr(request, "htmx", False)`` never
``request.htmx``, ``@require_POST`` before ``@login_required`` on the pure
mutator.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from suddenly.core.types import AuthenticatedRequest

from .models import Conversation
from .services import MessageService, NotMutualFollowersError


@login_required
def inbox(request: AuthenticatedRequest) -> HttpResponse:
    """List the current user's conversations, sorted by most recent activity."""
    from suddenly.core.views import htmx_render

    conversations = (
        Conversation.objects.filter(memberships__user=request.user)
        .select_related("participant_low", "participant_high")
        .distinct()
    )

    rows = []
    for conversation in conversations:
        other = MessageService.other_participant(conversation, request.user)
        rows.append(
            {
                "conversation": conversation,
                "other": other,
                "unread_count": MessageService.unread_for(conversation, request.user),
            }
        )

    return htmx_render(
        request,
        full_template="messaging/inbox.html",
        partial_template="messaging/_conversation_list.html",
        context={"rows": rows},
    )


@login_required
def thread(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Open a conversation thread; marks it read for the current user."""
    from suddenly.core.views import htmx_render

    conversation = get_object_or_404(
        Conversation.objects.select_related("participant_low", "participant_high"), pk=pk
    )
    if request.user.pk not in (conversation.participant_low_id, conversation.participant_high_id):
        raise Http404

    other = MessageService.other_participant(conversation, request.user)
    messages = conversation.messages.select_related("sender").order_by("created_at")
    MessageService.mark_read(conversation, request.user)

    return htmx_render(
        request,
        full_template="messaging/thread.html",
        partial_template="messaging/_message_list.html",
        context={"conversation": conversation, "other": other, "messages": messages},
    )


@login_required
def compose(request: AuthenticatedRequest) -> HttpResponse:
    """Composer, optionally pre-filled with a recipient candidate (``?to=<uuid>``, DEC-E7)."""
    from suddenly.characters.models import Follow
    from suddenly.core.views import htmx_render
    from suddenly.users.models import User

    recipient = None
    mutual = False
    to_id = request.GET.get("to", "")
    if to_id:
        recipient = User.objects.filter(pk=to_id).first()
        if recipient is not None and recipient != request.user:
            mutual = Follow.objects.are_mutual(request.user, recipient)

    return htmx_render(
        request,
        full_template="messaging/compose.html",
        partial_template="messaging/compose.html",
        context={"recipient": recipient, "mutual": mutual},
    )


@require_POST
@login_required
def send_message(request: AuthenticatedRequest) -> HttpResponse:
    """Send a direct message. 403 on a non-mutual recipient (DEC-E2), never a 500."""
    from suddenly.users.models import User

    recipient_id = request.POST.get("recipient", "")
    body = request.POST.get("body", "").strip()
    recipient = User.objects.filter(pk=recipient_id).first() if recipient_id else None

    if recipient is None or recipient == request.user or not body:
        return HttpResponseForbidden("Invalid recipient or empty message.")

    try:
        message = MessageService.send(request.user, recipient, body)
    except NotMutualFollowersError:
        return HttpResponseForbidden("You must be mutual followers to message this user.")

    return redirect("messaging:thread", pk=message.conversation_id)
