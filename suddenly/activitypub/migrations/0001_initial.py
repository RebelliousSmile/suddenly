"""Initial migration for activitypub app — creates FederatedServer table."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="FederatedServer",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("server_name", models.CharField(
                    help_text="Instance domain name (e.g. mastodon.social)",
                    max_length=255,
                    unique=True,
                )),
                ("application_type", models.CharField(
                    blank=True,
                    help_text="Software reported by NodeInfo (e.g. suddenly, mastodon)",
                    max_length=100,
                )),
                ("application_version", models.CharField(
                    blank=True,
                    help_text="Software version reported by NodeInfo",
                    max_length=50,
                )),
                ("status", models.CharField(
                    choices=[
                        ("UNKNOWN", "Inconnu"),
                        ("FEDERATED", "Fédéré"),
                        ("BLOCKED", "Bloqué"),
                    ],
                    db_index=True,
                    default="UNKNOWN",
                    max_length=20,
                )),
                ("user_count", models.IntegerField(
                    default=0,
                    help_text="Total user count from last NodeInfo fetch",
                )),
                ("last_checked", models.DateTimeField(
                    blank=True,
                    help_text="Timestamp of last successful NodeInfo fetch",
                    null=True,
                )),
            ],
            options={
                "verbose_name": "Instance fédérée",
                "verbose_name_plural": "Instances fédérées",
            },
        ),
        migrations.AddIndex(
            model_name="federatedserver",
            index=models.Index(fields=["server_name"], name="fedserver_name_idx"),
        ),
        migrations.AddIndex(
            model_name="federatedserver",
            index=models.Index(fields=["status"], name="fedserver_status_idx"),
        ),
        migrations.AddIndex(
            model_name="federatedserver",
            index=models.Index(fields=["application_type"], name="fedserver_type_idx"),
        ),
    ]
