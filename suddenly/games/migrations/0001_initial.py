# Generated migration for Suddenly games app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('game_system', models.CharField(blank=True, help_text='Ex: Mist Engine, D&D 5e', max_length=100)),
                ('is_public', models.BooleanField(default=True)),
                ('remote', models.BooleanField(default=False)),
                ('ap_id', models.URLField(blank=True, null=True, unique=True)),
                ('inbox_url', models.URLField(blank=True, null=True)),
                ('outbox_url', models.URLField(blank=True, null=True)),
                ('public_key', models.TextField(blank=True, help_text='PEM-encoded public key')),
                ('private_key', models.TextField(blank=True, help_text='PEM-encoded private key (local only)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='games', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('content', models.TextField(help_text='Markdown with @character mentions')),
                ('status', models.CharField(choices=[('draft', 'Brouillon'), ('published', 'Publié')], default='draft', max_length=20)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('remote', models.BooleanField(default=False)),
                ('ap_id', models.URLField(blank=True, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to=settings.AUTH_USER_MODEL)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='games.game')),
            ],
            options={
                'ordering': ['-published_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReportCast',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('new_character_name', models.CharField(blank=True, help_text='Name for new NPC (if character is null)', max_length=100)),
                ('new_character_description', models.TextField(blank=True, help_text='Description for new NPC')),
                ('role', models.CharField(choices=[('main', 'Principal'), ('supporting', 'Secondaire'), ('mentioned', 'Mentionné')], default='mentioned', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cast', to='games.report')),
            ],
            options={
                'ordering': ['role', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='game',
            index=models.Index(fields=['owner', 'is_public'], name='games_game_owner_i_8c7e9a_idx'),
        ),
        migrations.AddIndex(
            model_name='game',
            index=models.Index(fields=['is_public', 'updated_at'], name='games_game_is_publ_4e5a6b_idx'),
        ),
        migrations.AddIndex(
            model_name='report',
            index=models.Index(fields=['game', 'published_at'], name='games_repor_game_id_1a2b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='report',
            index=models.Index(fields=['status'], name='games_repor_status_4d5e6f_idx'),
        ),
        migrations.AddIndex(
            model_name='reportcast',
            index=models.Index(fields=['report'], name='games_repor_report__7g8h9i_idx'),
        ),
    ]
