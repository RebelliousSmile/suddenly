"""Add ReportCast.character FK after characters app is initialised.

ReportCast lives in the games app, but its character FK points to
characters.Character. This migration defers that FK to run after
characters.0001_initial, breaking the circular dependency.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0001_initial"),
        ("characters", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportcast",
            name="character",
            field=models.ForeignKey(
                blank=True,
                help_text="Existing character (null if creating new)",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cast_entries",
                to="characters.character",
            ),
        ),
    ]
