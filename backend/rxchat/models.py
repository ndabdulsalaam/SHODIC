import uuid
import ast
import json
import re

from django.db import models
from django.contrib.auth.models import User
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
    """A chat conversation (session)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='conversations')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    title = models.CharField(max_length=200, default='New Conversation')
    role_override = models.CharField(
        max_length=30, null=True, blank=True,
        help_text='Per-conversation role override (e.g. nurse, physician). '
                  'If set, overrides the user profile role for this conversation only.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at'], name='rxchat_conv_user_upd_idx'),
            models.Index(fields=['session_key', '-updated_at'], name='rxchat_conv_sess_upd_idx'),
        ]

    def __str__(self):
        return f"{self.title} ({self.id})"


class Message(models.Model):
    """A single message in a conversation."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    attachments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='rxchat_msg_conv_time_idx'),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}..."


# ---------------------------------------------------------------------------
# Data pipeline: RawData → CleanData → DrugChunk → Qdrant
# ---------------------------------------------------------------------------

class RawData(models.Model):
    """Admin-uploaded source file. No parsing on upload — a separate
    `parse_data` management command extracts text into CleanData."""
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, db_index=True)
    file = models.FileField(upload_to='raw_uploads/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'raw data'
        verbose_name_plural = 'raw data'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.source}: {self.file.name}"

    def delete(self, *args, **kwargs):
        # Cascade to CleanData rows (they cascade to DrugChunk + Qdrant).
        for clean in self.cleandata_set.all():
            clean.delete()
        return super().delete(*args, **kwargs)


def _text_to_json(source: str, raw_text: str) -> dict:
    """Convert plain extracted text back to a basic structured dict.

    The exact structure mirrors what the old parsers produced so that
    existing ingest_drugs logic can consume it unchanged.
    """
    parsed = _parse_structured_text(raw_text)
    if parsed:
        parsed.setdefault("source", source)
        parsed.setdefault("parsed_at", timezone.now().isoformat())
        return parsed

    return {
        "source": source,
        "raw_text": raw_text,
        "parsed_at": timezone.now().isoformat(),
    }


def _parse_structured_text(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if not text:
        return {}

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
        except (SyntaxError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            return parsed

    pairs = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = _normalise_key(key)
        if key:
            pairs[key] = value.strip()
    return pairs


def _normalise_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    aliases = {
        "who_essential_medicines_list_medicine": "medicine_name",
        "openfda_drug_label": "medicine_name",
        "nafdac_greenbook_product": "product_name",
    }
    return aliases.get(key, key)


class CleanData(models.Model):
    """Two-step reviewed data extracted from a RawData file (or a scraper).

    Stage 1 (draft):    ``parse_data`` writes plain extracted text to
                        ``raw_text``.  The admin shows a raw preview and an
                        auto-generated JSON preview.  The record is fully
                        editable at this stage.

    Stage 2 (accepted): The admin "Accept selected" action converts
                        ``raw_text`` → structured JSON in ``data`` and sets
                        ``status=accepted``.

    Stage 3 (chunked):  ``ingest_drugs`` reads accepted records, creates
                        DrugChunk rows, and sets ``status=chunked``.
    """
    STATUS_DRAFT = 'draft'
    STATUS_ACCEPTED = 'accepted'
    STATUS_CHUNKED = 'chunked'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_CHUNKED, 'Chunked'),
    ]

    raw = models.ForeignKey(
        RawData, on_delete=models.CASCADE,
        null=True, blank=True,
        help_text='Source upload this record was extracted from (null for scraped data).',
    )
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, db_index=True)
    source_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_DRAFT, db_index=True,
    )
    raw_text = models.TextField(
        blank=True,
        help_text='Plain extracted text — edit here before accepting.',
    )
    data = models.JSONField(
        default=dict, blank=True,
        help_text='Structured JSON — populated automatically on Accept.',
    )
    file_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'clean data'
        verbose_name_plural = 'clean data'
        ordering = ['source', 'source_id']
        constraints = [
            models.UniqueConstraint(fields=['source', 'source_id'], name='unique_clean_record'),
        ]
        permissions = [
            ('can_run_ingestion', 'Can run ingestion tasks'),
        ]

    def accept(self):
        """Convert raw_text → structured JSON and mark as accepted."""
        self.data = _text_to_json(self.source, self.raw_text)
        self.status = self.STATUS_ACCEPTED
        self.save(update_fields=['data', 'status', 'updated_at'])

    def reset_to_draft(self):
        """Clear accepted JSON and return to draft so raw_text can be re-edited."""
        point_ids = list(
            self.chunks.exclude(qdrant_point_id__isnull=True)
            .exclude(qdrant_point_id='')
            .values_list('qdrant_point_id', flat=True)
        )
        if point_ids:
            from .qdrant_service import delete_points  # noqa: PLC0415
            delete_points(point_ids)
        self.chunks.all().delete()
        self.data = {}
        self.status = self.STATUS_DRAFT
        self.save(update_fields=['data', 'status', 'updated_at'])

    def __str__(self):
        return f"{self.source}:{self.source_id} [{self.status}]"

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
    clean_data = models.ForeignKey(CleanData, on_delete=models.CASCADE, related_name='chunks')
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
        ordering = ['clean_data', 'chunk_index']
        constraints = [
            models.UniqueConstraint(fields=['clean_data', 'chunk_index'], name='unique_chunk_per_clean_data'),
        ]

    @property
    def source(self):
        return self.clean_data.source

    @property
    def drug_name(self):
        return (
            self.metadata.get('drug_name')
            or self.metadata.get('product_name')
            or self.metadata.get('medicine_name')
            or ''
        )

    @property
    def category(self):
        return self.metadata.get('category') or ''

    def mark_embedded(self, point_id: str):
        self.qdrant_point_id = point_id
        self.embedded_at = timezone.now()
        self.save(update_fields=['qdrant_point_id', 'embedded_at', 'updated_at'])

    def __str__(self):
        return f"{self.clean_data} chunk {self.chunk_index}"
