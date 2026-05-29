import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .ai_service import (
    _select_models,
    build_system_message,
    build_user_message,
    stream_ai_events,
)
from .models import Conversation, Message
from .serializers import ChatInputSerializer


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
        self.assertIn("Do not label it", system_message)
        self.assertNotIn("Follow-up question", system_message)
        self.assertNotIn("follow-up question", system_message.lower())
        self.assertNotIn("explicitly acknowledge that limitation", user_message)
        self.assertIn("Answer cautiously from general drug knowledge", user_message)
        self.assertIn("Do not tell the user that no background material", user_message)

    def test_source_notes_prompt_does_not_force_retrieval_disclaimer(self):
        user_message = build_user_message(
            "What should I know about diclofenac?",
            chunks=[{
                "source": "NAFDAC Greenbook excerpt",
                "text": "This excerpt does not include diclofenac.",
            }],
            role="patient",
        )

        self.assertIn("MODEL-ONLY BACKGROUND", user_message)
        self.assertIn("answer cautiously from general drug knowledge", user_message)
        self.assertIn("Do not mention this background or how it was selected", user_message)
        self.assertNotIn("RETRIEVED CONTEXT", user_message)
        self.assertNotIn("Answer based strictly", user_message)

    @override_settings(OPENROUTER_TEXT_MODEL="text-model")
    def test_model_selection_uses_text_model_only(self):
        self.assertEqual(_select_models(), ["text-model"])


class ChatInputSerializerTests(TestCase):
    def test_requires_message(self):
        serializer = ChatInputSerializer(data={"message": ""})

        self.assertFalse(serializer.is_valid())
        self.assertIn("message", serializer.errors)

    def test_trims_message(self):
        serializer = ChatInputSerializer(data={"message": "  What is metformin?  "})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["message"], "What is metformin?")

    def test_rejects_attachments_key(self):
        serializer = ChatInputSerializer(data={
            "message": "Review this",
            "attachments": [{"name": "rx.jpg"}],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)


class ChatAiServiceTests(TestCase):
    @override_settings(
        OPENROUTER_API_KEY="primary",
        OPENROUTER_BACKUP_API_KEY="backup",
        OPENROUTER_TEXT_MODEL="text-model",
    )
    @patch("rxchat.ai_service.retrieve_context", return_value=[])
    @patch("rxchat.ai_service._get_client")
    def test_backup_key_retries_when_primary_fails_before_streaming(self, mock_get_client, mock_retrieve):
        class Chunk:
            def __init__(self, text):
                self.choices = [type("Choice", (), {
                    "delta": type("Delta", (), {"content": text})(),
                    "finish_reason": None,
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

        events = list(stream_ai_events("What is metformin?", role="pharmacist"))
        response = "".join(e["content"] for e in events if isinstance(e, dict) and e.get("type") == "text")

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
    @patch("rxchat.ai_service.retrieve_context", return_value=[])
    @patch("rxchat.ai_service._get_client")
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

        events = list(stream_ai_events("What is metformin?", role="patient"))
        response = "".join(e["content"] for e in events if isinstance(e, dict) and e.get("type") == "text")

        self.assertEqual(captured_kwargs["max_tokens"], 123)
        self.assertIn("I'll pause there so the answer stays readable", response)
        self.assertIn("Which part would you like me to expand on next?", response)
        self.assertNotIn("Follow-up question:", response)
        mock_retrieve.assert_called_once()

    @override_settings(
        OPENROUTER_API_KEY="primary",
        OPENROUTER_BACKUP_API_KEY="",
        OPENROUTER_TEXT_MODEL="text-model",
    )
    @patch("rxchat.ai_service.retrieve_context", return_value=[])
    @patch("rxchat.ai_service._get_client")
    def test_stream_ai_events_emits_statuses_before_text(self, mock_get_client, mock_retrieve):
        class Chunk:
            def __init__(self, text):
                self.choices = [type("Choice", (), {
                    "delta": type("Delta", (), {"content": text})(),
                    "finish_reason": None,
                })()]

        client = type("Client", (), {})()
        client.chat = type("Chat", (), {})()
        client.chat.completions = type("Completions", (), {})()
        client.chat.completions.create = lambda **kwargs: iter([Chunk("Answer")])
        mock_get_client.return_value = client

        events = list(stream_ai_events("What is amlodipine?", role="patient"))
        status_labels = [event["label"] for event in events if event["type"] == "status"]
        text = "".join(event["content"] for event in events if event["type"] == "text")
        first_text_index = next(index for index, event in enumerate(events) if event["type"] == "text")
        last_status_index = max(index for index, event in enumerate(events) if event["type"] == "status")

        self.assertEqual(status_labels, ["Checking sources", "Thinking", "Generating"])
        self.assertLess(last_status_index, first_text_index)
        self.assertEqual(text, "Answer")
        mock_retrieve.assert_called_once()


class ChatApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _consume_stream(self, response):
        return b"".join(response.streaming_content).decode("utf-8")

    def _session_key(self, client=None):
        client = client or self.client
        session = client.session
        session["rxchat_test_session"] = True
        session.save()
        return session.session_key

    def _set_conversation_updated_at(self, conversation, updated_at):
        Conversation.objects.filter(id=conversation.id).update(updated_at=updated_at)
        conversation.refresh_from_db()
        return conversation.updated_at

    @patch("rxchat.views.stream_ai_events")
    def test_send_message_stream_includes_user_and_assistant_message_ids(self, mock_stream):
        mock_stream.return_value = iter([
            {"type": "status", "phase": "checking_sources", "label": "Checking sources"},
            "Hello",
            " from RxChat",
        ])

        response = self.client.post(
            "/rxchat/send/",
            {"message": "What is paracetamol used for?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = self._consume_stream(response)

        conversation = Conversation.objects.get()
        user_message = conversation.messages.get(role="user")
        assistant_message = conversation.messages.get(role="assistant")

        self.assertEqual(conversation.session_key, self.client.session.session_key)
        self.assertIn("event: meta", body)
        self.assertIn("event: status", body)
        self.assertLess(body.index("event: status"), body.index("data: Hello"))
        self.assertIn(f'"conversation_id": "{conversation.id}"', body)
        self.assertIn(f'"user_message_id": "{user_message.id}"', body)
        self.assertIn("event: done", body)
        self.assertIn(f'"message_id": "{assistant_message.id}"', body)
        self.assertEqual(assistant_message.content, "Hello from RxChat")

        args, kwargs = mock_stream.call_args
        self.assertEqual(args[0], "What is paracetamol used for?")
        self.assertEqual(kwargs["role"], "patient")
        self.assertNotIn("attachments", kwargs)

    @patch("rxchat.views.stream_ai_events")
    def test_send_message_saves_partial_assistant_when_stream_closes(self, mock_stream):
        mock_stream.return_value = iter(["Partial answer", " should not be consumed"])

        response = self.client.post(
            "/rxchat/send/",
            {"message": "What is amlodipine?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        iterator = iter(response.streaming_content)
        next(iterator)
        first_text_chunk = next(iterator).decode("utf-8")
        self.assertIn("Partial answer", first_text_chunk)

        if hasattr(iterator, "close"):
            iterator.close()
        response.close()

        conversation = Conversation.objects.get()
        assistant_message = conversation.messages.get(role="assistant")
        self.assertEqual(assistant_message.content, "Partial answer")

    def test_list_conversations_orders_newest_updated_first_for_session(self):
        session_key = self._session_key()
        older = Conversation.objects.create(session_key=session_key, title="Older")
        newer = Conversation.objects.create(session_key=session_key, title="Newer")
        now = timezone.now()
        self._set_conversation_updated_at(older, now - timedelta(days=3))
        self._set_conversation_updated_at(newer, now - timedelta(hours=1))

        response = self.client.get("/rxchat/conversations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(item["id"]) for item in response.data], [str(newer.id), str(older.id)])

    def test_list_conversations_is_limited_to_current_session(self):
        owner_key = self._session_key()
        other_client = APIClient()
        other_key = self._session_key(other_client)
        owned = Conversation.objects.create(session_key=owner_key, title="Visible")
        Conversation.objects.create(session_key=other_key, title="Hidden")

        response = self.client.get("/rxchat/conversations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(item["id"]) for item in response.data], [str(owned.id)])

    @patch("rxchat.views.stream_ai_events")
    def test_send_message_touches_existing_conversation_before_stream_is_consumed(self, mock_stream):
        mock_stream.return_value = iter(["Later answer"])
        session_key = self._session_key()
        conversation = Conversation.objects.create(session_key=session_key, title="Existing chat")
        stale_time = self._set_conversation_updated_at(conversation, timezone.now() - timedelta(days=2))

        response = self.client.post(
            "/rxchat/send/",
            {"message": "Follow up", "conversation_id": str(conversation.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        conversation.refresh_from_db()
        self.assertGreater(conversation.updated_at, stale_time)
        self.assertTrue(conversation.messages.filter(role="user", content="Follow up").exists())
        mock_stream.assert_not_called()

        body = self._consume_stream(response)
        self.assertIn('"conversation_updated_at"', body)

    def test_send_message_rejects_conversation_from_other_session(self):
        other_client = APIClient()
        other_key = self._session_key(other_client)
        conversation = Conversation.objects.create(session_key=other_key, title="Other session")

        response = self.client.post(
            "/rxchat/send/",
            {"message": "Follow up", "conversation_id": str(conversation.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    @patch("rxchat.views.stream_ai_events")
    def test_send_message_rejects_attachments_payload(self, mock_stream):
        response = self.client.post(
            "/rxchat/send/",
            {"message": "Review", "attachments": [{"name": "rx.jpg"}]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("attachments", response.data)
        self.assertFalse(Conversation.objects.exists())
        mock_stream.assert_not_called()

    def test_conversation_detail_is_limited_to_session(self):
        other_client = APIClient()
        other_key = self._session_key(other_client)
        conversation = Conversation.objects.create(session_key=other_key, title="Other chat")

        response = self.client.get(f"/rxchat/conversations/{conversation.id}/")

        self.assertEqual(response.status_code, 404)

    def test_rename_and_delete_conversation_for_session(self):
        session_key = self._session_key()
        conversation = Conversation.objects.create(session_key=session_key, title="Original")

        rename = self.client.patch(
            f"/rxchat/conversations/{conversation.id}/rename/",
            {"title": "Updated"},
            format="json",
        )
        self.assertEqual(rename.status_code, 200)
        conversation.refresh_from_db()
        self.assertEqual(conversation.title, "Updated")

        delete = self.client.delete(f"/rxchat/conversations/{conversation.id}/delete/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(Conversation.objects.filter(id=conversation.id).exists())

    @patch("rxchat.views.stream_ai_events")
    def test_edit_message_replaces_following_messages_and_streams_new_assistant_id(self, mock_stream):
        mock_stream.return_value = iter(["Edited answer"])
        session_key = self._session_key()
        conversation = Conversation.objects.create(session_key=session_key, title="Edit chat")
        user_message = Message.objects.create(conversation=conversation, role="user", content="Original")
        Message.objects.create(conversation=conversation, role="assistant", content="Old answer")

        response = self.client.put(
            f"/rxchat/messages/{user_message.id}/",
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

    @patch("rxchat.views.stream_ai_events")
    def test_resend_message_uses_user_message_and_replaces_old_assistant_response(self, mock_stream):
        mock_stream.return_value = iter(["Regenerated answer"])
        session_key = self._session_key()
        conversation = Conversation.objects.create(session_key=session_key, title="Resend chat")
        user_message = Message.objects.create(conversation=conversation, role="user", content="Question")
        old_assistant = Message.objects.create(conversation=conversation, role="assistant", content="Old answer")

        response = self.client.post(f"/rxchat/messages/{user_message.id}/resend/")

        self.assertEqual(response.status_code, 200)
        body = self._consume_stream(response)

        self.assertFalse(Message.objects.filter(id=old_assistant.id).exists())
        self.assertEqual(conversation.messages.count(), 2)
        assistant_message = conversation.messages.get(role="assistant")
        self.assertEqual(assistant_message.content, "Regenerated answer")
        self.assertIn(f'"message_id": "{assistant_message.id}"', body)

    def test_resend_rejects_assistant_message_id(self):
        session_key = self._session_key()
        conversation = Conversation.objects.create(session_key=session_key, title="Invalid resend")
        assistant_message = Message.objects.create(conversation=conversation, role="assistant", content="Answer")

        response = self.client.post(f"/rxchat/messages/{assistant_message.id}/resend/")

        self.assertEqual(response.status_code, 404)
