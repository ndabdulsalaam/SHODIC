from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ChatInputSerializer,
)
from .ai_service import get_ai_response


def _get_owner_filter(request):
    """Return filter kwargs for the current user or session."""
    if request.user.is_authenticated:
        return {'user': request.user}
    # Ensure session exists for anonymous users
    if not request.session.session_key:
        request.session.create()
    return {'session_key': request.session.session_key}


@api_view(['POST'])
def send_message(request):
    """
    POST /api/chat/send/
    Send a message and get an AI response.
    Body: { "message": "...", "conversation_id": "..." (optional) }
    """
    serializer = ChatInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user_text = serializer.validated_data['message']
    conv_id = serializer.validated_data.get('conversation_id')
    role = serializer.validated_data.get('role', 'patient')
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

    # Get AI response
    ai_text = get_ai_response(user_text, conversation_history=history, role=role)

    # Save AI message
    ai_message = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_text,
    )

    # Update conversation timestamp
    conversation.save()

    return Response({
        'conversation_id': str(conversation.id),
        'conversation_title': conversation.title,
        'message': {
            'id': str(ai_message.id),
            'role': 'assistant',
            'content': ai_text,
            'created_at': ai_message.created_at.isoformat(),
        }
    })


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
