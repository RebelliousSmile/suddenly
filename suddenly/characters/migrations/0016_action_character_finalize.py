import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0015_action_character_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="action",
            name="character",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="actions",
                to="characters.character",
            ),
        ),
        migrations.AlterField(
            model_name="action",
            name="trait_set",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="actions",
                to="characters.traitset",
            ),
        ),
    ]
