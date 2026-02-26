"""Add language preferences and fix indexes on User model."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        # email: make unique (AbstractUser default is non-unique)
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, default="", max_length=254, unique=True, verbose_name="email address"),
        ),
        # New language preference fields
        migrations.AddField(
            model_name="user",
            name="content_language",
            field=models.CharField(default="fr", max_length=10),
        ),
        migrations.AddField(
            model_name="user",
            name="preferred_languages",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="user",
            name="show_unlabeled_content",
            field=models.BooleanField(default=True),
        ),
        # remote: add db_index (boolean field used in AP filtering)
        migrations.AlterField(
            model_name="user",
            name="remote",
            field=models.BooleanField(db_index=True, default=False, help_text="True if federated user"),
        ),
    ]
