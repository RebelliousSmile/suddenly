"""
Management command: set a user as instance admin.

Usage:
    python manage.py set_admin <username>
"""

from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant instance-admin status to a user."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("username", type=str, help="Username of the user to promote.")

    def handle(self, *args: Any, **options: Any) -> None:
        user_model = get_user_model()
        username: str = options["username"]

        try:
            user = user_model.objects.get(username=username)
        except user_model.DoesNotExist:
            raise CommandError(f"User '{username}' not found.") from None

        if user.is_admin:
            self.stdout.write(
                self.style.WARNING(f"User '{username}' is already an admin. No change made.")
            )
            return

        user.is_admin = True
        user.save(update_fields=["is_admin"])
        self.stdout.write(self.style.SUCCESS(f"User '{username}' has been granted admin status."))
