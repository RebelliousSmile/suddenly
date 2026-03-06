"""
Signal handlers for the users app.

Initializes ActivityPub actor fields when a local user signs up.
"""

import logging

from allauth.account.signals import user_signed_up
from django.conf import settings
from django.dispatch import receiver

from suddenly.activitypub.signatures import generate_key_pair
from suddenly.users.models import User

logger = logging.getLogger(__name__)


@receiver(user_signed_up)
def initialize_activitypub_actor(
    request: object,
    user: User,
    **kwargs: object,
) -> None:
    """
    Populate AP fields for a newly registered local user.

    Skips remote users (federated accounts created via AP ingestion).
    Generates an RSA key pair and sets the canonical AP URLs.
    """
    if user.remote:
        return

    private_key, public_key = generate_key_pair()

    user.private_key = private_key
    user.public_key = public_key
    user.ap_id = f"{settings.AP_BASE_URL}/users/{user.username}"
    user.inbox_url = f"{user.ap_id}/inbox"
    user.outbox_url = f"{user.ap_id}/outbox"

    user.save(
        update_fields=[
            "private_key",
            "public_key",
            "ap_id",
            "inbox_url",
            "outbox_url",
        ]
    )
    logger.info("Initialized AP actor for user %s", user.username)
