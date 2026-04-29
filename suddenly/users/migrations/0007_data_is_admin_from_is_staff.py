"""
Data migration: set is_admin=True for all users where is_staff=True.
"""

from django.db import migrations


def set_is_admin_from_is_staff(apps: object, schema_editor: object) -> None:
    User = apps.get_model("users", "User")  # type: ignore[attr-defined]
    User.objects.filter(is_staff=True).update(is_admin=True)


def revert_is_admin_from_is_staff(apps: object, schema_editor: object) -> None:
    # Reversing is a no-op: we cannot know which is_admin values were set by
    # this migration vs. set manually, so we leave them as-is.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_add_is_admin"),
    ]

    operations = [
        migrations.RunPython(
            set_is_admin_from_is_staff,
            reverse_code=revert_is_admin_from_is_staff,
        ),
    ]
