"""
Data migration: populate tags_new (M2M) from tags (JSONField).
"""

from django.db import migrations


def migrate_tags_forward(apps, schema_editor):
    Character = apps.get_model("characters", "Character")
    Tag = apps.get_model("core", "Tag")

    for character in Character.objects.exclude(tags=[]):
        tag_objects = []
        for tag_name in character.tags:
            tag_name = tag_name.strip()
            if tag_name:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                tag_objects.append(tag)
        if tag_objects:
            character.tags_new.set(tag_objects)


def migrate_tags_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("characters", "0007_character_tags_add_m2m"),
    ]

    operations = [
        migrations.RunPython(migrate_tags_forward, migrate_tags_reverse),
    ]
