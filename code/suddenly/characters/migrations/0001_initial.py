# Generated migration for Suddenly characters app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('games', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='characters/')),
                ('status', models.CharField(choices=[('npc', 'PNJ'), ('pc', 'PJ'), ('claimed', 'Réclamé'), ('adopted', 'Adopté'), ('forked', 'Forké')], default='npc', max_length=20)),
                ('sheet_url', models.URLField(blank=True, help_text='Link to external character sheet', null=True)),
                ('remote', models.BooleanField(default=False)),
                ('ap_id', models.URLField(blank=True, null=True, unique=True)),
                ('inbox_url', models.URLField(blank=True, null=True)),
                ('outbox_url', models.URLField(blank=True, null=True)),
                ('public_key', models.TextField(blank=True, help_text='PEM-encoded public key')),
                ('private_key', models.TextField(blank=True, help_text='PEM-encoded private key (local only)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(help_text='Who created/mentioned this character first', on_delete=django.db.models.deletion.CASCADE, related_name='created_characters', to=settings.AUTH_USER_MODEL)),
                ('origin_game', models.ForeignKey(help_text='Game where this character was first mentioned', on_delete=django.db.models.deletion.CASCADE, related_name='characters', to='games.game')),
                ('owner', models.ForeignKey(blank=True, help_text='Current owner (null for unclaimed NPCs)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_characters', to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(blank=True, help_text='Parent character if this is a fork', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forks', to='characters.character')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Quote',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.TextField(help_text='The quote itself')),
                ('context', models.TextField(blank=True, help_text='Situation when this was said')),
                ('visibility', models.CharField(choices=[('ephemeral', 'Éphémère'), ('private', 'Privée'), ('public', 'Publique')], default='public', max_length=20)),
                ('expires_at', models.DateTimeField(blank=True, help_text='When this quote should disappear (for EPHEMERAL visibility)', null=True)),
                ('remote', models.BooleanField(default=False)),
                ('ap_id', models.URLField(blank=True, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(help_text='Who recorded this quote', on_delete=django.db.models.deletion.CASCADE, related_name='saved_quotes', to=settings.AUTH_USER_MODEL)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quotes', to='characters.character')),
                ('report', models.ForeignKey(blank=True, help_text='Source report if any', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quotes', to='games.report')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CharacterAppearance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('main', 'Principal'), ('supporting', 'Secondaire'), ('mentioned', 'Mentionné')], default='mentioned', max_length=20)),
                ('context', models.TextField(blank=True, help_text='Description of their role in this scene')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appearances', to='characters.character')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='character_appearances', to='games.report')),
            ],
            options={
                'ordering': ['role', 'character__name'],
                'unique_together': {('character', 'report')},
            },
        ),
        migrations.CreateModel(
            name='LinkRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('claim', 'Claim (rétcon)'), ('adopt', 'Adoption'), ('fork', 'Fork (dérivation)')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('accepted', 'Acceptée'), ('rejected', 'Refusée'), ('cancelled', 'Annulée')], default='pending', max_length=20)),
                ('message', models.TextField(help_text='Explanation of the request')),
                ('response_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('proposed_character', models.ForeignKey(blank=True, help_text='For claims: the existing PC being proposed', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='link_requests_proposed', to='characters.character')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='link_requests_made', to=settings.AUTH_USER_MODEL)),
                ('target_character', models.ForeignKey(help_text='The NPC being claimed/adopted/forked', on_delete=django.db.models.deletion.CASCADE, related_name='link_requests_received', to='characters.character')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CharacterLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('claim', 'Claim (rétcon)'), ('adopt', 'Adoption'), ('fork', 'Fork (dérivation)')], max_length=20)),
                ('description', models.TextField(blank=True, help_text='Nature of the link')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('link_request', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_link', to='characters.linkrequest')),
                ('source', models.ForeignKey(help_text='The PC', on_delete=django.db.models.deletion.CASCADE, related_name='links_as_source', to='characters.character')),
                ('target', models.ForeignKey(help_text='The former NPC', on_delete=django.db.models.deletion.CASCADE, related_name='links_as_target', to='characters.character')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SharedSequence',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('content', models.TextField(help_text='Markdown content')),
                ('status', models.CharField(choices=[('draft', 'Brouillon'), ('published', 'Publié')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('link', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='shared_sequence', to='characters.characterlink')),
            ],
        ),
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('object_id', models.UUIDField()),
                ('remote', models.BooleanField(default=False)),
                ('ap_id', models.URLField(blank=True, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(limit_choices_to={'model__in': ('user', 'character', 'game')}, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('follower', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='following', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('follower', 'content_type', 'object_id')},
            },
        ),
        # Add ReportCast.character FK (deferred to avoid circular dependency)
        migrations.AddField(
            model_name='reportcast',
            name='character',
            field=models.ForeignKey(blank=True, help_text='Existing character (null if creating new)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cast_entries', to='characters.character'),
        ),
        # Indexes
        migrations.AddIndex(
            model_name='character',
            index=models.Index(fields=['status'], name='char_status_idx'),
        ),
        migrations.AddIndex(
            model_name='character',
            index=models.Index(fields=['origin_game'], name='char_origin_idx'),
        ),
        migrations.AddIndex(
            model_name='character',
            index=models.Index(fields=['owner'], name='char_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='quote',
            index=models.Index(fields=['character', 'visibility'], name='quote_char_vis_idx'),
        ),
        migrations.AddIndex(
            model_name='quote',
            index=models.Index(fields=['visibility', 'expires_at'], name='quote_exp_idx'),
        ),
        migrations.AddIndex(
            model_name='characterappearance',
            index=models.Index(fields=['character', 'report'], name='appearance_idx'),
        ),
        migrations.AddIndex(
            model_name='linkrequest',
            index=models.Index(fields=['status', 'target_character'], name='linkreq_status_idx'),
        ),
        migrations.AddIndex(
            model_name='linkrequest',
            index=models.Index(fields=['requester', 'status'], name='linkreq_req_idx'),
        ),
        migrations.AddIndex(
            model_name='follow',
            index=models.Index(fields=['content_type', 'object_id'], name='follow_target_idx'),
        ),
        migrations.AddIndex(
            model_name='follow',
            index=models.Index(fields=['follower'], name='follow_follower_idx'),
        ),
    ]
