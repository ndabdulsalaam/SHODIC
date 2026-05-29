from rest_framework import serializers

from .models import Conversation, Message


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
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConversationListSerializer(_MessageCountMixin, serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count']


class ChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000, allow_blank=False, trim_whitespace=True)
    conversation_id = serializers.UUIDField(required=False)

    def validate_message(self, value):
        message = value.strip()
        if not message:
            raise serializers.ValidationError('Enter a message.')
        return message

    def validate(self, attrs):
        if 'attachments' in getattr(self, 'initial_data', {}):
            raise serializers.ValidationError({'attachments': 'Attachments are not supported.'})
        return attrs
