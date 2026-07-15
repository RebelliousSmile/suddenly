from django.db import migrations


def backfill_action_character(apps, schema_editor):
    Action = apps.get_model("characters", "Action")
    for action in Action.objects.all():
        action.character_id = action.trait_set.character_id
        action.save(update_fields=["character"])


def noop_reverse(apps, schema_editor):
    """No-op: character is repopulated by the forward function, never dropped."""


class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0014_action_character_add"),
    ]

    operations = [
        migrations.RunPython(backfill_action_character, noop_reverse),
    ]
