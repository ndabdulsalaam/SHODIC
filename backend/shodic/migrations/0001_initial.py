# Generated manually for the SHODIC free-session schema.

import django.db.models.deletion
import uuid
from django.db import migrations, models


SOURCE_CHOICES = [
    ('nafdac', 'NAFDAC'),
    ('openfda', 'OpenFDA'),
    ('neml', 'NEML'),
    ('nhia_stg', 'NHIA STG'),
    ('who', 'WHO EML'),
    ('nnmda', 'NNMDA'),
    ('emdex', 'EMDEX'),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('session_key', models.CharField(db_index=True, max_length=40)),
                ('title', models.CharField(default='New Conversation', max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-updated_at'],
                'indexes': [models.Index(fields=['session_key', '-updated_at'], name='shodic_conv_sess_upd_idx')],
            },
        ),
        migrations.CreateModel(
            name='RawSourceData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=SOURCE_CHOICES, db_index=True, max_length=30)),
                ('source_id', models.CharField(max_length=255)),
                ('raw_data', models.JSONField(default=dict)),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'raw data source',
                'verbose_name_plural': 'raw data sources',
                'ordering': ['source', 'source_id'],
                'permissions': [('can_run_ingestion', 'Can run ingestion tasks')],
                'constraints': [models.UniqueConstraint(fields=('source', 'source_id'), name='unique_raw_source_record')],
            },
        ),
        migrations.CreateModel(
            name='ScrapeProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=SOURCE_CHOICES, max_length=30, unique=True)),
                ('progress_data', models.JSONField(blank=True, default=dict)),
                ('last_run', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'scrape progress',
                'verbose_name_plural': 'scrape progress',
                'ordering': ['source'],
            },
        ),
        migrations.CreateModel(
            name='IngestionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=SOURCE_CHOICES + [('all', 'All')], db_index=True, max_length=30)),
                ('action', models.CharField(db_index=True, max_length=50)),
                ('status', models.CharField(db_index=True, max_length=30)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'ingestion log',
                'verbose_name_plural': 'ingestion logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SourceFileUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=SOURCE_CHOICES, max_length=30)),
                ('file', models.FileField(upload_to='source_uploads/')),
                ('description', models.TextField(blank=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('processed', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'upload source file',
                'verbose_name_plural': 'upload source files',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='DrugChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_index', models.PositiveIntegerField()),
                ('text', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('qdrant_point_id', models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ('embedded_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('raw_source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='shodic.rawsourcedata')),
            ],
            options={
                'verbose_name': 'drug chunk',
                'verbose_name_plural': 'drug chunks',
                'ordering': ['raw_source', 'chunk_index'],
                'constraints': [models.UniqueConstraint(fields=('raw_source', 'chunk_index'), name='unique_chunk_per_raw_source')],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=10)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='shodic.conversation')),
            ],
            options={
                'ordering': ['created_at'],
                'indexes': [models.Index(fields=['conversation', 'created_at'], name='shodic_msg_conv_time_idx')],
            },
        ),
    ]
