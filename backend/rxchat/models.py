import uuid

from django.db import models
from django.utils import timezone


SOURCE_NAFDAC = 'nafdac'
SOURCE_OPENFDA = 'openfda'
SOURCE_NEML = 'neml'
SOURCE_NHIA_STG = 'nhia_stg'
SOURCE_WHO = 'who'
SOURCE_NNMDA = 'nnmda'
SOURCE_EMDEX = 'emdex'

SOURCE_CHOICES = [
    (SOURCE_NAFDAC, 'NAFDAC'),
    (SOURCE_OPENFDA, 'OpenFDA'),
    (SOURCE_NEML, 'NEML'),
    (SOURCE_NHIA_STG, 'NHIA STG'),
    (SOURCE_WHO, 'WHO EML'),
    (SOURCE_NNMDA, 'NNMDA'),
    (SOURCE_EMDEX, 'EMDEX'),
]


class Conversation(models.Model):
    """A chat conversation owned by an anonymous browser session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=200, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['session_key', '-updated_at'], name='rxchat_conv_sess_upd_idx'),
        ]

    def __str__(self):
        return f"{self.title} ({self.id})"


class Message(models.Model):
    """A single text message in a conversation."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='rxchat_msg_conv_time_idx'),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}..."


class RawSourceData(models.Model):
    """Raw scraped, pulled, or uploaded source data stored in Postgres."""
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, db_index=True)
    source_id = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict)
    file_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'raw data source'
        verbose_name_plural = 'raw data sources'
        ordering = ['source', 'source_id']
        constraints = [
            models.UniqueConstraint(fields=['source', 'source_id'], name='unique_raw_source_record'),
        ]
        permissions = [
            ('can_run_ingestion', 'Can run ingestion tasks'),
        ]

    def __str__(self):
        return f"{self.source}:{self.source_id}"

    def delete(self, *args, **kwargs):
        point_ids = list(
            self.chunks.exclude(qdrant_point_id__isnull=True)
            .exclude(qdrant_point_id='')
            .values_list('qdrant_point_id', flat=True)
        )
        if point_ids:
            from .qdrant_service import delete_points  # noqa: PLC0415

            delete_points(point_ids)
        return super().delete(*args, **kwargs)


class DrugChunk(models.Model):
    """Processed text chunk ready for Qdrant embedding."""
    raw_source = models.ForeignKey(RawSourceData, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    qdrant_point_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    embedded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'drug chunk'
        verbose_name_plural = 'drug chunks'
        ordering = ['raw_source', 'chunk_index']
        constraints = [
            models.UniqueConstraint(fields=['raw_source', 'chunk_index'], name='unique_chunk_per_raw_source'),
        ]

    @property
    def source(self):
        return self.raw_source.source

    @property
    def drug_name(self):
        return self.metadata.get('drug_name') or self.metadata.get('product_name') or self.metadata.get('medicine_name') or ''

    @property
    def category(self):
        return self.metadata.get('category') or ''

    def mark_embedded(self, point_id: str):
        self.qdrant_point_id = point_id
        self.embedded_at = timezone.now()
        self.save(update_fields=['qdrant_point_id', 'embedded_at', 'updated_at'])

    def __str__(self):
        return f"{self.raw_source} chunk {self.chunk_index}"


class ScrapeProgress(models.Model):
    """Persistent scrape/pull progress, replacing local progress JSON."""
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, unique=True)
    progress_data = models.JSONField(default=dict, blank=True)
    last_run = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'scrape progress'
        verbose_name_plural = 'scrape progress'
        ordering = ['source']

    def __str__(self):
        return f"{self.source} progress"


class IngestionLog(models.Model):
    """Database-backed ingestion event log."""
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('ok', 'OK'),
        ('missing', 'Missing'),
        ('stale', 'Stale'),
        ('fresh', 'Fresh'),
    ]

    source = models.CharField(max_length=30, choices=SOURCE_CHOICES + [('all', 'All')], db_index=True)
    action = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=30, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ingestion log'
        verbose_name_plural = 'ingestion logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.source} {self.action} {self.status}"


class SourceFileUpload(models.Model):
    """Admin-uploaded source file for manual datasets."""
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    file = models.FileField(upload_to='source_uploads/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'upload source file'
        verbose_name_plural = 'upload source files'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.source}: {self.file.name}"

    def delete(self, *args, **kwargs):
        raw = RawSourceData.objects.filter(source=self.source, source_id=f"upload:{self.pk}").first()
        if raw:
            raw.delete()
        return super().delete(*args, **kwargs)
