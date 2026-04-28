from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0005_slug_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="tags",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
