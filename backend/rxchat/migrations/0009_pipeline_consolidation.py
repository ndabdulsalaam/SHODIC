import django.db.models.deletion
import json
from django.db import migrations, models


def migrate_existing_pipeline_data(apps, schema_editor):
    RawSourceData = apps.get_model('rxchat', 'RawSourceData')
    SourceFileUpload = apps.get_model('rxchat', 'SourceFileUpload')
    RawData = apps.get_model('rxchat', 'RawData')
    CleanData = apps.get_model('rxchat', 'CleanData')
    DrugChunk = apps.get_model('rxchat', 'DrugChunk')

    upload_map = {}
    for upload in SourceFileUpload.objects.all().order_by('pk'):
        raw = RawData.objects.create(
            source=upload.source,
            file=upload.file,
            description=upload.description,
        )
        upload_map[(upload.source, upload.pk)] = raw.pk

    for raw_source in RawSourceData.objects.all().order_by('pk'):
        raw_upload_id = None
        if raw_source.source_id.startswith('upload:'):
            try:
                old_upload_id = int(raw_source.source_id.split(':', 1)[1])
            except (TypeError, ValueError):
                old_upload_id = None
            raw_upload_id = upload_map.get((raw_source.source, old_upload_id))

        has_chunks = DrugChunk.objects.filter(raw_source_id=raw_source.pk).exists()
        raw_data = raw_source.raw_data or {}
        clean = CleanData.objects.create(
            raw_id=raw_upload_id,
            source=raw_source.source,
            source_id=raw_source.source_id,
            status='chunked' if has_chunks else 'accepted' if raw_data else 'draft',
            raw_text=json.dumps(raw_data, ensure_ascii=False, default=str) if raw_data else '',
            data=raw_data,
            file_name=raw_source.file_name,
        )
        DrugChunk.objects.filter(raw_source_id=raw_source.pk).update(clean_data_id=clean.pk)

    DrugChunk.objects.filter(clean_data_id__isnull=True).delete()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rxchat', '0008_add_conversation_message_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='CleanData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('nafdac', 'NAFDAC'), ('openfda', 'OpenFDA'), ('neml', 'NEML'), ('nhia_stg', 'NHIA STG'), ('who', 'WHO EML'), ('nnmda', 'NNMDA'), ('emdex', 'EMDEX')], db_index=True, max_length=30)),
                ('source_id', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('accepted', 'Accepted'), ('chunked', 'Chunked')], db_index=True, default='draft', max_length=20)),
                ('raw_text', models.TextField(blank=True, help_text='Plain extracted text — edit here before accepting.')),
                ('data', models.JSONField(blank=True, default=dict, help_text='Structured JSON — populated automatically on Accept.')),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'clean data',
                'verbose_name_plural': 'clean data',
                'ordering': ['source', 'source_id'],
                'permissions': [('can_run_ingestion', 'Can run ingestion tasks')],
            },
        ),
        migrations.CreateModel(
            name='RawData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('nafdac', 'NAFDAC'), ('openfda', 'OpenFDA'), ('neml', 'NEML'), ('nhia_stg', 'NHIA STG'), ('who', 'WHO EML'), ('nnmda', 'NNMDA'), ('emdex', 'EMDEX')], db_index=True, max_length=30)),
                ('file', models.FileField(upload_to='raw_uploads/')),
                ('description', models.TextField(blank=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'raw data',
                'verbose_name_plural': 'raw data',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.AlterModelOptions(
            name='drugchunk',
            options={'ordering': ['clean_data', 'chunk_index'], 'verbose_name': 'drug chunk', 'verbose_name_plural': 'drug chunks'},
        ),
        migrations.RemoveConstraint(
            model_name='drugchunk',
            name='unique_chunk_per_raw_source',
        ),
        migrations.AddField(
            model_name='drugchunk',
            name='clean_data',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='rxchat.cleandata'),
        ),
        migrations.AddField(
            model_name='cleandata',
            name='raw',
            field=models.ForeignKey(blank=True, help_text='Source upload this record was extracted from (null for scraped data).', null=True, on_delete=django.db.models.deletion.CASCADE, to='rxchat.rawdata'),
        ),
        migrations.RunPython(migrate_existing_pipeline_data, reverse_noop),
        migrations.DeleteModel(
            name='IngestionLog',
        ),
        migrations.RemoveConstraint(
            model_name='rawsourcedata',
            name='unique_raw_source_record',
        ),
        migrations.DeleteModel(
            name='ScrapeProgress',
        ),
        migrations.DeleteModel(
            name='SourceFileUpload',
        ),
        migrations.RemoveField(
            model_name='drugchunk',
            name='raw_source',
        ),
        migrations.AlterField(
            model_name='drugchunk',
            name='clean_data',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='rxchat.cleandata'),
        ),
        migrations.AddConstraint(
            model_name='drugchunk',
            constraint=models.UniqueConstraint(fields=('clean_data', 'chunk_index'), name='unique_chunk_per_clean_data'),
        ),
        migrations.AddConstraint(
            model_name='cleandata',
            constraint=models.UniqueConstraint(fields=('source', 'source_id'), name='unique_clean_record'),
        ),
        migrations.DeleteModel(
            name='RawSourceData',
        ),
    ]
