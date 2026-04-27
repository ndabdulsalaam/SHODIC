import base64
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .ai_service import (
    _build_pdf_plugin,
    _build_user_content,
    _select_model,
    build_system_message,
    build_user_message,
    stream_ai_response,
)
from .models import Conversation, Message
from .serializers import ChatInputSerializer


def data_url(mime_type, payload=b"file"):
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def image_attachment(name="prescription.jpg"):
    return {
        "kind": "image",
        "name": name,
        "type": "image/jpeg",
        "data_url": data_url("image/jpeg"),
        "preview_data_url": data_url("image/jpeg", b"preview"),
    }


def pdf_attachment(name="report.pdf"):
    return {
        "kind": "file",
        "name": name,
        "type": "application/pdf",
        "data_url": data_url("application/pdf"),
    }


class ChatPromptTests(TestCase):
    def test_no_context_prompt_discourages_robotic_disclaimers(self):
        system_message = build_system_message("pharmacist")
        user_message = build_user_message(
            "What are common adverse effects of metformin?",
            chunks=[],
            role="pharmacist",
        )

        self.assertIn("Do not use headings such as \"Safety Disclaimer\"", system_message)
        self.assertIn("normal conversation", system_message)
        self.assertIn("response budget", system_message)
        self.assertIn("Follow-up question", system_message)
        self.assertNotIn("explicitly acknowledge that limitation", user_message)
        self.assertIn("Do not announce the missing retrieval context", user_message)

    @override_settings(
        OPENROUTER_TEXT_MODEL="text-model",
        OPENROUTER_VISION_MODEL="vision-model",
    )
    def test_model_selection_uses_vision_when_any_image_is_present(self):
        self.assertEqual(_select_model([]), "text-model")
        self.assertEqual(_select_model([pdf_attachment()]), "text-model")
        self.assertEqual(
            _select_model([pdf_attachment(), image_attachment()]),
            "vision-model",
        )

    def test_multimodal_content_includes_multiple_images_and_pdf(self):
        content = _build_user_content(
            "Review these attachments",
            [image_attachment("a.jpg"), image_attachment("b.jpg"), pdf_attachment()],
        )

        self.assertEqual(content[0], {"type": "text", "text": "Review these attachments"})
        self.assertEqual([part["type"] for part in content], ["text", "image_url", "image_url", "file"])
        self.assertEqual(content[3]["file"]["filename"], "report.pdf")

    def test_pdf_plugin_uses_cloudflare_ai_parser(self):
        self.assertIsNone(_build_pdf_plugin([image_attachment()]))
        self.assertEqual(
            _build_pdf_plugin([pdf_attachment()]),
            [{"id": "file-parser", "pdf": {"engine": "cloudflare-ai"}}],
        )


class ChatInputSerializerTests(TestCase):
    def test_rejects_attachment_only_message_while_paused(self):
        serializer = ChatInputSerializer(data={
            "message": "",
            "attachments": [image_attachment()],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("Attachments are temporarily unavailable.", str(serializer.errors))

    def test_requires_message_or_attachment(self):
        serializer = ChatInputSerializer(data={"message": ""})

        self.assertFalse(serializer.is_valid())

    def test_rejects_more_than_three_attachments(self):
        serializer = ChatInputSerializer(data={
            "message": "Review",
            "attachments": [
                image_attachment("one.jpg"),
                image_attachment("two.jpg"),
                image_attachment("three.jpg"),
                image_attachment("four.jpg"),
            ],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)

    def test_rejects_legacy_doc_files(self):
        serializer = ChatInputSerializer(data={
            "message": "Review",
            "attachments": [{
                "kind": "file",
                "name": "old.doc",
                "type": "application/msword",
                "data_url": data_url("application/msword"),
            }],
        })

        self.assertFalse(serializer.is_valid())


class ChatAiServiceTests(TestCase):
    @override_settings(
        OPENROUTER_API_KEY="primary",
        OPENROUTER_BACKUP_API_KEY="backup",
        OPENROUTER_TEXT_MODEL="text-model",
        OPENROUTER_VISION_MODEL="vision-model",
    )
    @patch("chat.ai_service.retrieve_context", return_value=[])
    @patch("chat.ai_service._get_client")
    def test_backup_key_retries_when_primary_fails_before_streaming(self, mock_get_client, mock_retrieve):
        class Chunk:
            def __init__(self, text):
                self.choices = [type("Choice", (), {
                    "delta": type("Delta", (), {"content": text})()
                })()]

        primary_client = type("Client", (), {})()
        backup_client = type("Client", (), {})()
        primary_client.chat = type("Chat", (), {})()
        backup_client.chat = type("Chat", (), {})()
        primary_client.chat.completions = type("Completions", (), {})()
        backup_client.chat.completions = type("Completions", (), {})()

        def fail_create(**kwargs):
            raise Exception("rate limited")

        def backup_create(**kwargs):
            return iter([Chunk("Hello"), Chunk(" from backup")])

        primary_client.chat.completions.create = fail_create
        backup_client.chat.completions.create = backup_create
        mock_get_client.side_effect = [primary_client, backup_client]

        response = "".join(stream_ai_response("What is metformin?", role="pharmacist"))

        self.assertEqual(response, "Hello from backup")
        self.assertEqual(mock_get_client.call_count, 2)
        mock_retrieve.assert_called_once()

    @override_settings(
        OPENROUTER_API_KEY="primary",
        OPENROUTER_BACKUP_API_KEY="",
        OPENROUTER_TEXT_MODEL="text-model",
        OPENROUTER_TEXT_MAX_TOKENS=123,
        OPENROUTER_REASONING_MAX_TOKENS=456,
    )
    @patch("chat.ai_service.retrieve_context", return_value=[])
    @patch("chat.ai_service._get_client")
    def test_length_finish_reason_adds_clean_stop_and_uses_budget(self, mock_get_client, mock_retrieve):
        captured_kwargs = {}

        class Chunk:
            def __init__(self, text="", finish_reason=None):
                self.choices = [type("Choice", (), {
                    "delta": type("Delta", (), {"content": text})(),
                    "finish_reason": finish_reason,
                })()]

        client = type("Client", (), {})()
        client.chat = type("Chat", (), {})()
        client.chat.completions = type("Completions", (), {})()

        def create(**kwargs):
            captured_kwargs.update(kwargs)
            return iter([Chunk("Partial answer"), Chunk(finish_reason="length")])

        client.chat.completions.create = create
        mock_get_client.return_value = client

        response = "".join(stream_ai_response("What is metformin?", role="patient"))

        self.assertEqual(captured_kwargs["max_tokens"], 123)
        self.assertIn("stays within RxChat's response limit", response)
        self.assertIn("Follow-up question:", response)
        mock_retrieve.assert_called_once()


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

    @patch("chat.views.stream_ai_response")
    def test_send_message_meta_event_escapes_json_title(self, mock_stream):
        mock_stream.return_value = iter(["Safe answer"])

        response = self.client.post(
            "/api/chat/send/",
            {"message": 'What about "quoted" dosing?'},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = self._consume_stream(response)
        meta_line = next(
            line for line in body.splitlines()
            if line.startswith('data: {"conversation_id"')
        )
        meta = json.loads(meta_line.removeprefix("data: "))

        self.assertEqual(meta["conversation_title"], 'What about "quoted" dosing?')

    @patch("chat.views.stream_ai_response")
    def test_send_message_rejects_new_attachments_while_paused(self, mock_stream):
        mock_stream.return_value = iter(["Attachment answer"])

        response = self.client.post(
            "/api/chat/send/",
            {
                "message": "",
                "attachments": [image_attachment()],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Attachments are temporarily unavailable.", str(response.data))
        self.assertFalse(Conversation.objects.exists())
        mock_stream.assert_not_called()

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

    @patch("chat.views.stream_ai_response")
    def test_edit_allows_image_attachment_message_with_saved_preview(self, mock_stream):
        mock_stream.return_value = iter(["Updated image answer"])
        user = User.objects.create_user(username="attachment-edit@example.com", email="attachment-edit@example.com", password="password123")
        conversation = Conversation.objects.create(user=user, title="Attachment edit")
        user_message = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Please review the attached files/images.",
            attachments=[{
                "kind": "image",
                "name": "rx.jpg",
                "type": "image/jpeg",
                "preview_data_url": data_url("image/jpeg", b"preview"),
            }],
        )
        Message.objects.create(conversation=conversation, role="assistant", content="Old answer")

        self.client.force_authenticate(user=user)
        response = self.client.put(
            f"/api/chat/messages/{user_message.id}/",
            {"content": "Updated"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self._consume_stream(response)

        user_message.refresh_from_db()
        self.assertEqual(user_message.content, "Updated")
        self.assertEqual(conversation.messages.count(), 2)

        args, kwargs = mock_stream.call_args
        self.assertEqual(args[0], "Updated")
        self.assertEqual(kwargs["attachments"][0]["name"], "rx.jpg")
        self.assertEqual(kwargs["attachments"][0]["data_url"], data_url("image/jpeg", b"preview"))

    @patch("chat.views.stream_ai_response")
    def test_resend_allows_image_attachment_message_with_saved_preview(self, mock_stream):
        mock_stream.return_value = iter(["Regenerated image answer"])
        user = User.objects.create_user(username="attachment-resend-image@example.com", email="attachment-resend-image@example.com", password="password123")
        conversation = Conversation.objects.create(user=user, title="Attachment resend image")
        user_message = Message.objects.create(
            conversation=conversation,
            role="user",
            content="",
            attachments=[{
                "kind": "image",
                "name": "rx.jpg",
                "type": "image/jpeg",
                "preview_data_url": data_url("image/jpeg", b"preview"),
            }],
        )
        Message.objects.create(conversation=conversation, role="assistant", content="Old answer")

        self.client.force_authenticate(user=user)
        response = self.client.post(f"/api/chat/messages/{user_message.id}/resend/")

        self.assertEqual(response.status_code, 200)
        self._consume_stream(response)

        args, kwargs = mock_stream.call_args
        self.assertEqual(args[0], "Please review the attached files/images.")
        self.assertEqual(kwargs["attachments"][0]["name"], "rx.jpg")
        self.assertEqual(kwargs["attachments"][0]["data_url"], data_url("image/jpeg", b"preview"))

    def test_resend_rejects_attachment_message(self):
        user = User.objects.create_user(username="attachment-resend@example.com", email="attachment-resend@example.com", password="password123")
        conversation = Conversation.objects.create(user=user, title="Attachment resend")
        user_message = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Please review the attached files/images.",
            attachments=[{"kind": "file", "name": "report.pdf", "type": "application/pdf"}],
        )

        self.client.force_authenticate(user=user)
        response = self.client.post(f"/api/chat/messages/{user_message.id}/resend/")

        self.assertEqual(response.status_code, 400)
