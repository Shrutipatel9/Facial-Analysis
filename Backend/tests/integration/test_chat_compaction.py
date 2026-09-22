"""Integration tests for chat conversation compaction (Milestone 4, Phase
27, FR-030). Every scenario uses the existing mocked-AI-client pattern
(ai_recorder, or a local recording fake client for tests that need to
inspect exactly what was sent) -- zero real API calls, matching BR-006 and
this project's "never spend real tokens in automated tests" posture."""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services import chat_service
from app.services.chat_service import PreparedReply, _build_system_prompt, _maybe_compact, stream_reply
from tests.conftest import _FakeStream

pytestmark = pytest.mark.asyncio


class RecordingChatClient:
    """Records the exact `messages` payload of every call, streaming or
    not -- ai_recorder (conftest.py) tracks call *count* but not call
    *content*, and this module's tests need to assert on content (does a
    compacted call actually include the stored summary, does the older
    history genuinely get left out). Reuses conftest.py's own _FakeStream
    for the streaming shape rather than a second, divergent fake."""

    def __init__(self, summary_text: str = "Summary of the earlier conversation.") -> None:
        self.calls: list[list[dict[str, str]]] = []
        self._summary_text = summary_text

    async def create(self, **kwargs):
        self.calls.append(kwargs["messages"])
        if kwargs.get("stream"):
            return _FakeStream(("ok",))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._summary_text))]
        )


@pytest.fixture
def fake_chat_client(monkeypatch) -> RecordingChatClient:
    fake = RecordingChatClient()
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake.create)))
    monkeypatch.setattr("app.services.ai_narrative_service.get_ai_client", lambda: client)
    return fake


async def _seed_conversation(db: AsyncSession, message_count: int) -> Conversation:
    user = User(email=f"chat-compaction-{uuid.uuid4().hex}@example.com", password_hash="not-a-real-hash")
    db.add(user)
    await db.flush()
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    await db.flush()
    for i in range(message_count):
        db.add(
            Message(
                conversation_id=conversation.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"message {i}",
            )
        )
    await db.commit()
    await db.refresh(conversation)
    return conversation


class TestMaybeCompact:
    async def test_under_threshold_is_a_noop(self, db: AsyncSession, fake_chat_client):
        settings = get_settings()
        conversation = await _seed_conversation(db, settings.chat_compaction_threshold_messages)
        history = await chat_service._load_messages(db, conversation.id)

        result = await _maybe_compact(db, conversation, history)

        assert result == history
        assert conversation.summary is None
        assert fake_chat_client.calls == []

    async def test_over_threshold_triggers_exactly_one_compaction_call(self, db: AsyncSession, fake_chat_client):
        settings = get_settings()
        conversation = await _seed_conversation(db, settings.chat_compaction_threshold_messages + 1)
        history = await chat_service._load_messages(db, conversation.id)

        result = await _maybe_compact(db, conversation, history)

        assert len(fake_chat_client.calls) == 1
        assert len(result) == settings.chat_compaction_keep_recent_messages
        assert result == history[-settings.chat_compaction_keep_recent_messages :]
        assert conversation.summary == "Summary of the earlier conversation."

    async def test_older_messages_are_never_deleted_from_the_database(self, db: AsyncSession, fake_chat_client):
        settings = get_settings()
        conversation = await _seed_conversation(db, settings.chat_compaction_threshold_messages + 1)
        history_before = await chat_service._load_messages(db, conversation.id)

        await _maybe_compact(db, conversation, history_before)

        history_after = await chat_service._load_messages(db, conversation.id)
        assert len(history_after) == len(history_before)  # nothing deleted, only excluded from the model call

    async def test_second_compaction_folds_the_prior_summary_forward(self, db: AsyncSession, fake_chat_client):
        settings = get_settings()
        conversation = await _seed_conversation(db, settings.chat_compaction_threshold_messages + 1)
        history = await chat_service._load_messages(db, conversation.id)
        await _maybe_compact(db, conversation, history)
        assert conversation.summary is not None

        # Add enough new messages to cross the threshold again.
        for i in range(settings.chat_compaction_threshold_messages + 1):
            db.add(Message(conversation_id=conversation.id, role="user", content=f"second round {i}"))
        await db.commit()
        history_2 = await chat_service._load_messages(db, conversation.id)

        await _maybe_compact(db, conversation, history_2)

        assert len(fake_chat_client.calls) == 2
        second_call_user_content = fake_chat_client.calls[1][1]["content"]
        assert "Summary of the earlier conversation." in second_call_user_content

    async def test_compaction_failure_falls_back_to_full_history(self, db: AsyncSession, monkeypatch):
        from openai import OpenAIError

        async def _broken_create(**kwargs):
            raise OpenAIError("simulated provider failure")

        broken_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_broken_create)))
        monkeypatch.setattr("app.services.ai_narrative_service.get_ai_client", lambda: broken_client)

        settings = get_settings()
        conversation = await _seed_conversation(db, settings.chat_compaction_threshold_messages + 1)
        history = await chat_service._load_messages(db, conversation.id)

        result = await _maybe_compact(db, conversation, history)

        assert result == history  # never silently drops context on a provider failure
        assert conversation.summary is None


class TestBuildSystemPromptSummaryClause:
    async def test_no_summary_omits_the_clause(self):
        prompt = _build_system_prompt({}, "", None)
        assert "Summary of earlier parts" not in prompt

    async def test_summary_is_included_when_present(self):
        prompt = _build_system_prompt({}, "", "The user asked about their skin routine.")
        assert "The user asked about their skin routine." in prompt
        assert "Summary of earlier parts" in prompt


class TestStreamReplyUsesCompaction:
    async def test_stream_reply_sends_compacted_history_when_over_threshold(
        self, db: AsyncSession, fake_chat_client
    ):
        settings = get_settings()
        conversation = await _seed_conversation(db, settings.chat_compaction_threshold_messages)
        # One more message (the "current" user turn prepare_reply would have
        # persisted) pushes this over the threshold.
        db.add(Message(conversation_id=conversation.id, role="user", content="one more to cross the threshold"))
        await db.commit()

        prepared = PreparedReply(conversation=conversation, sections={}, refused=False)
        async for _ in stream_reply(db, prepared):
            pass

        # Exactly two real calls: one compaction (non-streaming), one reply (streaming).
        assert len(fake_chat_client.calls) == 2
        reply_call_messages = fake_chat_client.calls[1]
        # system + compacted recent window, never the full 31-message history.
        assert len(reply_call_messages) == 1 + settings.chat_compaction_keep_recent_messages
        assert "Summary of the earlier conversation." in reply_call_messages[0]["content"]
