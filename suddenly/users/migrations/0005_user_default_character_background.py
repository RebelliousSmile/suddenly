from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_add_interface_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="default_character_background",
            field=models.ImageField(blank=True, null=True, upload_to="backgrounds/"),
        ),
    ]
