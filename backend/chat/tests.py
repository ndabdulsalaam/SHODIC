from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Conversation, Message


class ChatApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _consume_stream(self, response):
        return b"".join(response.streaming_content).decode("utf-8")

    @patch("chat.views.stream_ai_response")
    def test_send_message_stream_includes_user_and_assistant_message_ids(self, mock_stream):
        mock_stream.return_value = iter(["Hello", " from RxChat"])

        response = self.client.post(
            "/api/chat/send/",
            {"message": "What is paracetamol used for?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = self._consume_stream(response)

        conversation = Conversation.objects.get()
        user_message = conversation.messages.get(role="user")
        assistant_message = conversation.messages.get(role="assistant")

        self.assertIn("event: meta", body)
        self.assertIn(f'"conversation_id": "{conversation.id}"', body)
        self.assertIn(f'"user_message_id": "{user_message.id}"', body)
        self.assertIn("event: done", body)
        self.assertIn(f'"message_id": "{assistant_message.id}"', body)
        self.assertEqual(assistant_message.content, "Hello from RxChat")

    def test_conversation_detail_is_limited_to_owner(self):
        owner = User.objects.create_user(username="owner@example.com", email="owner@example.com", password="password123")
        other = User.objects.create_user(username="other@example.com", email="other@example.com", password="password123")
        conversation = Conversation.objects.create(user=owner, title="Owner chat")

        self.client.force_authenticate(user=other)
        response = self.client.get(f"/api/chat/conversations/{conversation.id}/")

        self.assertEqual(response.status_code, 404)

    @patch("chat.views.stream_ai_response")
    def test_edit_message_replaces_following_messages_and_streams_new_assistant_id(self, mock_stream):
        mock_stream.return_value = iter(["Edited answer"])
        user = User.objects.create_user(username="editor@example.com", email="editor@example.com", password="password123")
        conversation = Conversation.objects.create(user=user, title="Edit chat")
        user_message = Message.objects.create(conversation=conversation, role="user", content="Original")
        Message.objects.create(conversation=conversation, role="assistant", content="Old answer")

        self.client.force_authenticate(user=user)
        response = self.client.put(
            f"/api/chat/messages/{user_message.id}/",
            {"content": "Updated question"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = self._consume_stream(response)

        user_message.refresh_from_db()
        self.assertEqual(user_message.content, "Updated question")
        self.assertEqual(conversation.messages.count(), 2)

        assistant_message = conversation.messages.get(role="assistant")
        self.assertEqual(assistant_message.content, "Edited answer")
        self.assertIn(f'"edited_message_id": "{user_message.id}"', body)
        self.assertIn(f'"message_id": "{assistant_message.id}"', body)

    @patch("chat.views.stream_ai_response")
    def test_resend_message_uses_user_message_and_replaces_old_assistant_response(self, mock_stream):
        mock_stream.return_value = iter(["Regenerated answer"])
        user = User.objects.create_user(username="resend@example.com", email="resend@example.com", password="password123")
        conversation = Conversation.objects.create(user=user, title="Resend chat")
        user_message = Message.objects.create(conversation=conversation, role="user", content="Question")
        old_assistant = Message.objects.create(conversation=conversation, role="assistant", content="Old answer")

        self.client.force_authenticate(user=user)
        response = self.client.post(f"/api/chat/messages/{user_message.id}/resend/")

        self.assertEqual(response.status_code, 200)
        body = self._consume_stream(response)

        self.assertFalse(Message.objects.filter(id=old_assistant.id).exists())
        self.assertEqual(conversation.messages.count(), 2)
        assistant_message = conversation.messages.get(role="assistant")
        self.assertEqual(assistant_message.content, "Regenerated answer")
        self.assertIn(f'"message_id": "{assistant_message.id}"', body)

    def test_resend_rejects_assistant_message_id(self):
        user = User.objects.create_user(username="assistant-id@example.com", email="assistant-id@example.com", password="password123")
        conversation = Conversation.objects.create(user=user, title="Invalid resend")
        assistant_message = Message.objects.create(conversation=conversation, role="assistant", content="Answer")

        self.client.force_authenticate(user=user)
        response = self.client.post(f"/api/chat/messages/{assistant_message.id}/resend/")

        self.assertEqual(response.status_code, 404)
