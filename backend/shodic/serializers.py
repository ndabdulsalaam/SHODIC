from rest_framework import serializers

from .models import (
    Conversation,
    Message,
    PATIENT_SEX_FEMALE,
    PATIENT_SEX_CHOICES,
    PREGNANCY_NOT_APPLICABLE,
    PREGNANCY_STATUS_CHOICES,
    ROLE_CHOICES,
    ROLE_PATIENT,
    SUBJECT_CHOICES,
    SUBJECT_SELF,
)


SESSION_CONTEXT_FIELDS = ['role', 'subject', 'patient_sex', 'pregnancy_status']


def normalize_session_context(attrs):
    patient_sex = attrs.get('patient_sex', '')
    pregnancy_status = attrs.get('pregnancy_status', '')

    if patient_sex == PATIENT_SEX_FEMALE:
        if not pregnancy_status or pregnancy_status == PREGNANCY_NOT_APPLICABLE:
            raise serializers.ValidationError({
                'pregnancy_status': 'Select pregnancy or breastfeeding status for female patients.',
            })
        return attrs

    if patient_sex:
        attrs['pregnancy_status'] = PREGNANCY_NOT_APPLICABLE

    return attrs


class SessionContextSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ROLE_CHOICES, required=False, default=ROLE_PATIENT)
    subject = serializers.ChoiceField(choices=SUBJECT_CHOICES, required=False, default=SUBJECT_SELF)
    patient_sex = serializers.ChoiceField(choices=PATIENT_SEX_CHOICES, required=False, allow_blank=True)
    pregnancy_status = serializers.ChoiceField(
        choices=PREGNANCY_STATUS_CHOICES,
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        return normalize_session_context(attrs)


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'created_at']
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
        fields = [
            'id',
            'title',
            'role',
            'subject',
            'patient_sex',
            'pregnancy_status',
            'created_at',
            'updated_at',
            'message_count',
            'messages',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConversationListSerializer(_MessageCountMixin, serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'role',
            'subject',
            'patient_sex',
            'pregnancy_status',
            'created_at',
            'updated_at',
            'message_count',
        ]


class ChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000, allow_blank=False, trim_whitespace=True)
    conversation_id = serializers.UUIDField(required=False)
    role = serializers.ChoiceField(choices=ROLE_CHOICES, required=False, default=ROLE_PATIENT)
    subject = serializers.ChoiceField(choices=SUBJECT_CHOICES, required=False, default=SUBJECT_SELF)
    patient_sex = serializers.ChoiceField(choices=PATIENT_SEX_CHOICES, required=False, allow_blank=True)
    pregnancy_status = serializers.ChoiceField(
        choices=PREGNANCY_STATUS_CHOICES,
        required=False,
        allow_blank=True,
    )

    def validate_message(self, value):
        message = value.strip()
        if not message:
            raise serializers.ValidationError('Enter a message.')
        return message

    def validate(self, attrs):
        if 'attachments' in getattr(self, 'initial_data', {}):
            raise serializers.ValidationError({'attachments': 'Attachments are not supported.'})
        return normalize_session_context(attrs)
