# Generated manually - remove JSONField tags and rename M2M tags_new → tags

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0008_data_character_tags"),
        ("core", "0004_add_instancesettings"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="character",
            name="tags",
        ),
        migrations.RenameField(
            model_name="character",
            old_name="tags_new",
            new_name="tags",
        ),
    ]
