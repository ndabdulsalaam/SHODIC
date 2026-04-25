import tempfile

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ChatInputSerializer,
    parse_data_url,
)
from .ai_service import stream_ai_response


DEFAULT_ATTACHMENT_PROMPT = "Please review the attached files/images."
OFFICE_EXTENSIONS = {'.docx', '.pptx', '.xls', '.xlsx'}
MAX_DOCUMENT_CHARS_PER_ATTACHMENT = 20000
MAX_DOCUMENT_CHARS_TOTAL = 45000


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


def _attachment_metadata(attachments):
    """Return safe-to-persist metadata without original uploaded data."""
    metadata = []
    for attachment in attachments:
        item = {
            'kind': attachment['kind'],
            'name': attachment['name'],
            'type': attachment['type'],
            'size_bytes': attachment.get('size_bytes', 0),
        }
        if attachment['kind'] == 'image' and attachment.get('preview_data_url'):
            item['preview_data_url'] = attachment['preview_data_url']
        metadata.append(item)
    return metadata


def _llm_attachments(attachments):
    """Only images and PDFs are sent to OpenRouter as binary content parts."""
    return [
        {
            'kind': attachment['kind'],
            'name': attachment['name'],
            'type': attachment['type'],
            'data_url': attachment['data_url'],
        }
        for attachment in attachments
        if attachment['kind'] == 'image' or attachment['extension'] == '.pdf'
    ]


def _stored_image_attachments_for_llm(attachments):
    """Rebuild image-only LLM attachments from persisted preview metadata."""
    llm_attachments = []
    for attachment in attachments or []:
        if attachment.get('kind') != 'image' or not attachment.get('preview_data_url'):
            return None

        llm_attachments.append({
            'kind': 'image',
            'name': attachment.get('name') or 'image',
            'type': attachment.get('type') or 'image/jpeg',
            'data_url': attachment['preview_data_url'],
        })

    return llm_attachments


def _truncate_document_text(text, remaining_chars):
    allowed = min(MAX_DOCUMENT_CHARS_PER_ATTACHMENT, remaining_chars)
    if allowed <= 0:
        return "[Content omitted because the extracted document limit was reached.]"
    text = (text or '').strip()
    if len(text) <= allowed:
        return text
    return (
        text[:allowed].rstrip()
        + "\n\n[Content truncated because the extracted document was too long.]"
    )


def _extract_office_document_sections(attachments):
    """Extract Office documents to markdown text with MarkItDown."""
    office_attachments = [
        attachment for attachment in attachments
        if attachment.get('extension') in OFFICE_EXTENSIONS
    ]
    if not office_attachments:
        return []

    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise ValueError(
            "Document extraction is unavailable. Please install markitdown and try again."
        ) from exc

    converter = MarkItDown()
    sections = []
    used_chars = 0

    for attachment in office_attachments:
        try:
            _, file_bytes = parse_data_url(attachment['data_url'])
            with tempfile.NamedTemporaryFile(suffix=attachment['extension']) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                result = converter.convert(tmp.name)
        except Exception as exc:
            raise ValueError(f"Could not extract text from {attachment['name']}.") from exc

        extracted = getattr(result, 'text_content', '') or ''
        text = _truncate_document_text(
            extracted,
            MAX_DOCUMENT_CHARS_TOTAL - used_chars,
        )
        used_chars += len(text)
        sections.append({
            'name': attachment['name'],
            'text': text,
        })

    return sections



@api_view(['POST'])
def send_message(request):
    """
    POST /api/chat/send/
    Send a message and get a streamed AI response via SSE.
    Body: { "message": "...", "conversation_id": "..." }
    """
    serializer = ChatInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    requested_text = serializer.validated_data.get('message', '')
    attachments = serializer.validated_data.get('attachments', [])
    user_text = requested_text
    ai_user_text = requested_text or DEFAULT_ATTACHMENT_PROMPT
    conv_id = serializer.validated_data.get('conversation_id')

    try:
        document_sections = _extract_office_document_sections(attachments)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    safe_attachments = _attachment_metadata(attachments)
    ai_attachments = _llm_attachments(attachments)

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
        title_source = requested_text or ', '.join(item['name'] for item in safe_attachments) or DEFAULT_ATTACHMENT_PROMPT
        title = title_source[:50] + ('...' if len(title_source) > 50 else '')
        conversation = Conversation.objects.create(title=title, **owner)

    # Save user message
    user_message = Message.objects.create(
        conversation=conversation,
        role='user',
        content=user_text,
        attachments=safe_attachments,
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
        yield (
            "event: meta\n"
            f"data: {{\"conversation_id\": \"{conversation.id}\", "
            f"\"conversation_title\": \"{conversation.title}\", "
            f"\"user_message_id\": \"{user_message.id}\"}}\n\n"
        )

        for chunk in stream_ai_response(
            ai_user_text,
            conversation_history=history,
            role=effective_role,
            attachments=ai_attachments,
            document_sections=document_sections,
        ):
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

    llm_attachments = _stored_image_attachments_for_llm(message.attachments)
    if message.attachments and llm_attachments is None:
        return Response(
            {'error': 'Only image messages with saved previews can be edited. Please send a new message with the files attached again.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not content and not llm_attachments:
        return Response(
            {'error': 'Content cannot be empty'},
            status=status.HTTP_400_BAD_REQUEST
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
    ai_user_text = content or DEFAULT_ATTACHMENT_PROMPT


    def event_stream():
        full_response = []

        yield f"event: meta\ndata: {{\"conversation_id\": \"{conversation.id}\", \"edited_message_id\": \"{message.id}\"}}\n\n"

        for chunk in stream_ai_response(
            ai_user_text,
            conversation_history=history,
            role=effective_role,
            attachments=llm_attachments,
        ):
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

    llm_attachments = _stored_image_attachments_for_llm(message.attachments)
    if message.attachments and llm_attachments is None:
        return Response(
            {'error': 'Only image messages with saved previews can be regenerated. Please send a new message with the files attached again.'},
            status=status.HTTP_400_BAD_REQUEST
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
    ai_user_text = message.content or DEFAULT_ATTACHMENT_PROMPT


    def event_stream():
        full_response = []

        yield f"event: meta\ndata: {{\"conversation_id\": \"{conversation.id}\"}}\n\n"

        for chunk in stream_ai_response(
            ai_user_text,
            conversation_history=history,
            role=effective_role,
            attachments=llm_attachments,
        ):
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
