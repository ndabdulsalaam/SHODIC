from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ChatInputSerializer,
)
from .ai_service import stream_ai_response


def _get_owner_filter(request):
    """Return filter kwargs for the current user or session."""
    if request.user.is_authenticated:
        return {'user': request.user}
    # Ensure session exists for anonymous users
    if not request.session.session_key:
        request.session.create()
    return {'session_key': request.session.session_key}


def _get_user_role(request):
    """Get the user's role from their profile, defaulting to 'patient'."""
    if request.user.is_authenticated:
        try:
            return request.user.profile.role or 'patient'
        except Exception:
            pass
    return 'patient'





@api_view(['POST'])
def send_message(request):
    """
    POST /api/chat/send/
    Send a message and get a streamed AI response via SSE.
    Body: { "message": "...", "conversation_id": "..." }
    """
    serializer = ChatInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user_text = serializer.validated_data['message']
    conv_id = serializer.validated_data.get('conversation_id')


    # Role comes from the user's profile, not the request body
    role = _get_user_role(request)
    owner = _get_owner_filter(request)

    # Get or create conversation
    if conv_id:
        try:
            conversation = Conversation.objects.get(id=conv_id, **owner)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        title = user_text[:50] + ('...' if len(user_text) > 50 else '')
        conversation = Conversation.objects.create(title=title, **owner)

    # Save user message
    Message.objects.create(
        conversation=conversation,
        role='user',
        content=user_text,
    )

    # Get conversation history for context
    history = list(
        conversation.messages
        .order_by('created_at')
        .values('role', 'content')
    )[:-1]  # Exclude the message we just saved (already in user_text)

    # Check for role override on the conversation
    effective_role = getattr(conversation, 'role_override', None) or role

    def event_stream():
        """Generator that yields SSE-formatted chunks and saves the full response."""
        full_response = []

        # Send conversation metadata as the first event
        yield f"event: meta\ndata: {{\"conversation_id\": \"{conversation.id}\", \"conversation_title\": \"{conversation.title}\"}}\n\n"

        for chunk in stream_ai_response(user_text, conversation_history=history, role=effective_role):
            full_response.append(chunk)
            # Escape newlines for SSE data field
            escaped = chunk.replace('\n', '\\n')
            yield f"data: {escaped}\n\n"

        # Save the complete AI message to the database
        ai_content = "".join(full_response)
        ai_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=ai_content,
        )
        conversation.save()

        # Send done event with message ID
        yield f"event: done\ndata: {{\"message_id\": \"{ai_message.id}\"}}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['GET'])
def list_conversations(request):
    """
    GET /api/chat/conversations/
    List all conversations for the current user/session.
    """
    owner = _get_owner_filter(request)
    conversations = Conversation.objects.filter(**owner)
    serializer = ConversationListSerializer(conversations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_conversation(request, conversation_id):
    """
    GET /api/chat/conversations/<id>/
    Get a conversation with all messages.
    """
    owner = _get_owner_filter(request)
    try:
        conversation = Conversation.objects.get(id=conversation_id, **owner)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data)


@api_view(['DELETE'])
def delete_conversation(request, conversation_id):
    """
    DELETE /api/chat/conversations/<id>/
    Delete a conversation.
    """
    owner = _get_owner_filter(request)
    try:
        conversation = Conversation.objects.get(id=conversation_id, **owner)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    conversation.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
def rename_conversation(request, conversation_id):
    """
    PATCH /api/chat/conversations/<id>/rename/
    Rename a conversation title.
    Body: { "title": "New Title" }
    """
    owner = _get_owner_filter(request)
    try:
        conversation = Conversation.objects.get(id=conversation_id, **owner)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    title = request.data.get('title', '').strip()
    if not title:
        return Response(
            {'error': 'Title cannot be empty'},
            status=status.HTTP_400_BAD_REQUEST
        )

    conversation.title = title[:200]
    conversation.save()
    return Response({'id': str(conversation.id), 'title': conversation.title})


@api_view(['PUT'])
def edit_message(request, message_id):
    """
    PUT /api/chat/messages/<id>/
    Edit a user message and regenerate the AI response.
    This deletes all messages after the edited one, updates it,
    and streams a new AI response.
    Body: { "content": "Updated question" }
    """
    owner = _get_owner_filter(request)
    content = request.data.get('content', '').strip()
    if not content:
        return Response(
            {'error': 'Content cannot be empty'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        message = Message.objects.get(id=message_id, role='user')
        conversation = message.conversation
        # Verify ownership
        if owner.get('user'):
            assert conversation.user == owner['user']
        else:
            assert conversation.session_key == owner.get('session_key')
    except (Message.DoesNotExist, AssertionError):
        return Response(
            {'error': 'Message not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Delete all messages after this one
    Message.objects.filter(
        conversation=conversation,
        created_at__gt=message.created_at,
    ).delete()

    # Update the message content
    message.content = content
    message.save()

    # Get conversation history up to the edited message
    history = list(
        conversation.messages
        .order_by('created_at')
        .values('role', 'content')
    )[:-1]

    role = _get_user_role(request)
    effective_role = getattr(conversation, 'role_override', None) or role


    def event_stream():
        full_response = []

        yield f"event: meta\ndata: {{\"conversation_id\": \"{conversation.id}\", \"edited_message_id\": \"{message.id}\"}}\n\n"

        for chunk in stream_ai_response(content, conversation_history=history, role=effective_role):
            full_response.append(chunk)
            escaped = chunk.replace('\n', '\\n')
            yield f"data: {escaped}\n\n"

        ai_content = "".join(full_response)
        ai_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=ai_content,
        )
        conversation.save()

        yield f"event: done\ndata: {{\"message_id\": \"{ai_message.id}\"}}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['POST'])
def resend_message(request, message_id):
    """
    POST /api/chat/messages/<id>/resend/
    Resend a user message to regenerate the AI response.
    Deletes the existing AI response (if any) after this message
    and streams a new one.
    """
    owner = _get_owner_filter(request)

    try:
        message = Message.objects.get(id=message_id, role='user')
        conversation = message.conversation
        if owner.get('user'):
            assert conversation.user == owner['user']
        else:
            assert conversation.session_key == owner.get('session_key')
    except (Message.DoesNotExist, AssertionError):
        return Response(
            {'error': 'Message not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Delete all messages after this user message
    Message.objects.filter(
        conversation=conversation,
        created_at__gt=message.created_at,
    ).delete()

    # Get conversation history up to and including this message
    history = list(
        conversation.messages
        .order_by('created_at')
        .values('role', 'content')
    )[:-1]

    role = _get_user_role(request)
    effective_role = getattr(conversation, 'role_override', None) or role


    def event_stream():
        full_response = []

        yield f"event: meta\ndata: {{\"conversation_id\": \"{conversation.id}\"}}\n\n"

        for chunk in stream_ai_response(message.content, conversation_history=history, role=effective_role):
            full_response.append(chunk)
            escaped = chunk.replace('\n', '\\n')
            yield f"data: {escaped}\n\n"

        ai_content = "".join(full_response)
        ai_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=ai_content,
        )
        conversation.save()

        yield f"event: done\ndata: {{\"message_id\": \"{ai_message.id}\"}}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

