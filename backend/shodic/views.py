import json

from django.db.models import Count
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ai_service import stream_ai_events
from .models import Conversation, Message
from .serializers import (
    ChatInputSerializer,
    ConversationListSerializer,
    ConversationSerializer,
    SESSION_CONTEXT_FIELDS,
    SessionContextSerializer,
)


MAX_HISTORY_MESSAGES = 10


def _get_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_owner_filter(request):
    return {'session_key': _get_session_key(request)}


def _conversation_context_payload(conversation):
    return {field: getattr(conversation, field) for field in SESSION_CONTEXT_FIELDS}


def _validated_context_data(serializer):
    return {
        field: serializer.validated_data[field]
        for field in SESSION_CONTEXT_FIELDS
        if field in serializer.validated_data
    }


def _get_owned_user_message(message_id, owner):
    return Message.objects.select_related('conversation').get(
        id=message_id,
        role='user',
        conversation__session_key=owner['session_key'],
    )


def _conversation_history_before(conversation, message, limit=MAX_HISTORY_MESSAGES):
    recent = list(
        conversation.messages
        .filter(created_at__lt=message.created_at)
        .order_by('-created_at')
        .values('role', 'content')[:limit]
    )
    return list(reversed(recent))


def _touch_conversation(conversation):
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])
    return conversation.updated_at


def _sse_json(event, payload):
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _sse_text(chunk):
    escaped = chunk.replace('\r', '').replace('\n', '\\n')
    return f"data: {escaped}\n\n"


def _normalize_ai_event(event):
    if isinstance(event, str):
        return {'type': 'text', 'content': event}
    if not isinstance(event, dict):
        return None

    event_type = event.get('type')
    if event_type == 'status':
        return {
            'type': 'status',
            'phase': event.get('phase'),
            'label': event.get('label') or event.get('phase') or 'Thinking',
        }
    if event_type == 'text':
        return {
            'type': 'text',
            'content': event.get('content', ''),
        }
    return None


def _save_streamed_assistant(conversation, full_response, stream_state):
    if stream_state.get('saved'):
        return stream_state.get('message')

    ai_content = ''.join(full_response)
    if not ai_content:
        stream_state['saved'] = True
        return None

    ai_message = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_content,
    )
    updated_at = _touch_conversation(conversation)
    stream_state['saved'] = True
    stream_state['message'] = ai_message
    stream_state['updated_at'] = updated_at
    return ai_message


def _stream_chat_completion(*, conversation, ai_user_text, history, meta, role, patient_context):
    """Return an SSE response that streams and persists one assistant reply."""

    def event_stream():
        full_response = []
        stream_state = {'saved': False}

        try:
            yield _sse_json('meta', meta)

            for raw_event in stream_ai_events(
                ai_user_text,
                conversation_history=history,
                role=role,
                patient_context=patient_context,
            ):
                event = _normalize_ai_event(raw_event)
                if not event:
                    continue

                if event['type'] == 'status':
                    yield _sse_json('status', {
                        'phase': event['phase'],
                        'label': event['label'],
                    })
                    continue

                chunk = event['content']
                if not chunk:
                    continue
                full_response.append(chunk)
                yield _sse_text(chunk)

            ai_message = _save_streamed_assistant(conversation, full_response, stream_state)
            if ai_message:
                yield _sse_json('done', {
                    'conversation_id': str(conversation.id),
                    'conversation_updated_at': stream_state['updated_at'].isoformat(),
                    'message_id': str(ai_message.id),
                })
        finally:
            _save_streamed_assistant(conversation, full_response, stream_state)

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['POST'])
def send_message(request):
    """Send a text message and stream the AI response via SSE."""
    serializer = ChatInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user_text = serializer.validated_data['message']
    conv_id = serializer.validated_data.get('conversation_id')
    owner = _get_owner_filter(request)
    context_data = _validated_context_data(serializer)

    if conv_id:
        try:
            conversation = Conversation.objects.get(id=conv_id, **owner)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        title = user_text[:50] + ('...' if len(user_text) > 50 else '')
        conversation = Conversation.objects.create(title=title, **owner, **context_data)

    user_message = Message.objects.create(
        conversation=conversation,
        role='user',
        content=user_text,
    )
    conversation_updated_at = _touch_conversation(conversation)
    history = _conversation_history_before(conversation, user_message)

    return _stream_chat_completion(
        conversation=conversation,
        ai_user_text=user_text,
        history=history,
        meta={
            'conversation_id': str(conversation.id),
            'conversation_title': conversation.title,
            'conversation_created_at': conversation.created_at.isoformat(),
            'conversation_updated_at': conversation_updated_at.isoformat(),
            'user_message_id': str(user_message.id),
            **_conversation_context_payload(conversation),
        },
        role=conversation.role,
        patient_context=_conversation_context_payload(conversation),
    )


@api_view(['GET'])
def list_conversations(request):
    """List all conversations for the current browser session."""
    owner = _get_owner_filter(request)
    conversations = (
        Conversation.objects
        .filter(**owner)
        .annotate(message_count=Count('messages'))
        .order_by('-updated_at')
    )
    serializer = ConversationListSerializer(conversations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_conversation(request, conversation_id):
    """Get a conversation with all messages for the current session."""
    owner = _get_owner_filter(request)
    try:
        conversation = (
            Conversation.objects
            .prefetch_related('messages')
            .annotate(message_count=Count('messages'))
            .get(id=conversation_id, **owner)
        )
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data)


@api_view(['PATCH'])
def update_conversation_context(request, conversation_id):
    """Update role and patient context for future replies in a conversation."""
    owner = _get_owner_filter(request)
    try:
        conversation = Conversation.objects.get(id=conversation_id, **owner)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = SessionContextSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    update_fields = []
    for field, value in _validated_context_data(serializer).items():
        setattr(conversation, field, value)
        update_fields.append(field)

    if update_fields:
        conversation.save(update_fields=update_fields)

    return Response(ConversationSerializer(conversation).data)


@api_view(['DELETE'])
def delete_conversation(request, conversation_id):
    """Delete a conversation owned by the current session."""
    owner = _get_owner_filter(request)
    try:
        conversation = Conversation.objects.get(id=conversation_id, **owner)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND,
        )
    conversation.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
def rename_conversation(request, conversation_id):
    """Rename a conversation title owned by the current session."""
    owner = _get_owner_filter(request)
    try:
        conversation = Conversation.objects.get(id=conversation_id, **owner)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    title = request.data.get('title', '').strip()
    if not title:
        return Response(
            {'error': 'Title cannot be empty'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    conversation.title = title[:200]
    conversation.save(update_fields=['title'])
    return Response({'id': str(conversation.id), 'title': conversation.title})


@api_view(['PUT'])
def edit_message(request, message_id):
    """Edit a user message and regenerate the assistant response."""
    owner = _get_owner_filter(request)
    content = request.data.get('content', '').strip()

    if not content:
        return Response(
            {'error': 'Content cannot be empty'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        message = _get_owned_user_message(message_id, owner)
        conversation = message.conversation
    except Message.DoesNotExist:
        return Response(
            {'error': 'Message not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    Message.objects.filter(
        conversation=conversation,
        created_at__gt=message.created_at,
    ).delete()

    message.content = content
    message.save(update_fields=['content'])
    conversation_updated_at = _touch_conversation(conversation)
    history = _conversation_history_before(conversation, message)

    return _stream_chat_completion(
        conversation=conversation,
        ai_user_text=content,
        history=history,
        meta={
            'conversation_id': str(conversation.id),
            'conversation_updated_at': conversation_updated_at.isoformat(),
            'edited_message_id': str(message.id),
            **_conversation_context_payload(conversation),
        },
        role=conversation.role,
        patient_context=_conversation_context_payload(conversation),
    )


@api_view(['POST'])
def resend_message(request, message_id):
    """Regenerate an assistant response from a previous user message."""
    owner = _get_owner_filter(request)

    try:
        message = _get_owned_user_message(message_id, owner)
        conversation = message.conversation
    except Message.DoesNotExist:
        return Response(
            {'error': 'Message not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    Message.objects.filter(
        conversation=conversation,
        created_at__gt=message.created_at,
    ).delete()
    conversation_updated_at = _touch_conversation(conversation)
    history = _conversation_history_before(conversation, message)

    return _stream_chat_completion(
        conversation=conversation,
        ai_user_text=message.content,
        history=history,
        meta={
            'conversation_id': str(conversation.id),
            'conversation_updated_at': conversation_updated_at.isoformat(),
            **_conversation_context_payload(conversation),
        },
        role=conversation.role,
        patient_context=_conversation_context_payload(conversation),
    )
