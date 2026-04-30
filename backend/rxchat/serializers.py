import base64
import binascii
import re
from pathlib import Path

from django.conf import settings
from rest_framework import serializers
from .models import Conversation, Message


MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_PREVIEW_BYTES = 512 * 1024

IMAGE_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

DOCUMENT_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
}
DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xls', '.xlsx'}

DATA_URL_RE = re.compile(r'^data:(?P<mime>[-\w.+/]+);base64,(?P<data>.+)$', re.DOTALL)


def parse_data_url(value):
    """Return (mime_type, decoded_bytes) for a base64 data URL."""
    match = DATA_URL_RE.match(value or '')
    if not match:
        raise serializers.ValidationError('Attachment data must be a base64 data URL.')

    try:
        decoded = base64.b64decode(match.group('data'), validate=True)
    except (binascii.Error, ValueError):
        raise serializers.ValidationError('Attachment data is not valid base64.')

    return match.group('mime').lower(), decoded


def get_attachment_extension(name):
    return Path(name or '').suffix.lower()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'attachments', 'created_at']
        read_only_fields = ['id', 'created_at']


class _MessageCountMixin:
    def get_message_count(self, obj):
        annotated_count = getattr(obj, 'message_count', None)
        if annotated_count is not None:
            return annotated_count
        return obj.messages.count()


class ConversationSerializer(_MessageCountMixin, serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConversationListSerializer(_MessageCountMixin, serializers.ModelSerializer):
    """Lightweight serializer for sidebar list (no messages)."""
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count']


class ChatInputSerializer(serializers.Serializer):
    """Validates incoming chat messages."""
    message = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    conversation_id = serializers.UUIDField(required=False)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )

    def validate_attachments(self, attachments):
        if attachments and not getattr(settings, 'RXCHAT_ATTACHMENTS_ENABLED', False):
            raise serializers.ValidationError('Attachments are temporarily unavailable.')

        if len(attachments) > MAX_ATTACHMENTS:
            raise serializers.ValidationError(f'Attach up to {MAX_ATTACHMENTS} files per message.')

        validated = []
        for index, attachment in enumerate(attachments, start=1):
            name = str(attachment.get('name') or '').strip()
            mime_type = str(attachment.get('type') or '').strip().lower()
            kind = str(attachment.get('kind') or '').strip().lower()
            data_url = str(attachment.get('data_url') or '').strip()
            preview_data_url = str(attachment.get('preview_data_url') or '').strip()
            extension = get_attachment_extension(name)

            if not name:
                raise serializers.ValidationError(f'Attachment {index} is missing a filename.')
            if not data_url:
                raise serializers.ValidationError(f'Attachment {index} is missing file data.')

            data_mime_type, decoded = parse_data_url(data_url)
            size_bytes = len(decoded)
            if size_bytes > MAX_ATTACHMENT_BYTES:
                raise serializers.ValidationError(f'{name} exceeds the 10 MB upload limit.')

            effective_type = mime_type or data_mime_type
            if effective_type != data_mime_type:
                raise serializers.ValidationError(f'{name} has mismatched file type metadata.')

            is_image = effective_type in IMAGE_MIME_TYPES and extension in IMAGE_EXTENSIONS
            is_document = effective_type in DOCUMENT_MIME_TYPES and extension in DOCUMENT_EXTENSIONS

            if extension == '.doc':
                raise serializers.ValidationError('Legacy .doc files are not supported. Please upload .docx.')
            if not is_image and not is_document:
                raise serializers.ValidationError(f'{name} is not a supported attachment type.')

            expected_kind = 'image' if is_image else 'file'
            if kind and kind != expected_kind:
                raise serializers.ValidationError(f'{name} has an invalid attachment kind.')

            if preview_data_url:
                preview_mime_type, preview_bytes = parse_data_url(preview_data_url)
                if preview_mime_type not in IMAGE_MIME_TYPES:
                    raise serializers.ValidationError(f'{name} preview must be an image data URL.')
                if len(preview_bytes) > MAX_PREVIEW_BYTES:
                    raise serializers.ValidationError(f'{name} preview is too large.')

            validated.append({
                'kind': expected_kind,
                'name': name,
                'type': effective_type,
                'data_url': data_url,
                'preview_data_url': preview_data_url,
                'extension': extension,
                'size_bytes': size_bytes,
            })

        return validated

    def validate(self, attrs):
        message = (attrs.get('message') or '').strip()
        attachments = attrs.get('attachments') or []
        if not message and not attachments:
            raise serializers.ValidationError('Enter a message or attach a file.')
        attrs['message'] = message
        attrs['attachments'] = attachments
        return attrs
