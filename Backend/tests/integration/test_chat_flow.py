"""Integration tests for the AI Beauty Assistant chat endpoints (FR-019,
Milestone 2 Phase 12). No real AI provider calls run in tests (BR-006) --
the ai_recorder fixture's fake client covers both the streaming chat-
completion shape and the narrative call shape. These tests cover the
endpoint/service contract, not real conversational quality."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from tests.conftest import _FAKE_STREAM_CHUNKS
from tests.integration.test_report_flow import _auth_headers_and_user_id, _complete_paid_analysis

pytestmark = pytest.mark.asyncio

_EXPECTED_STREAMED_TEXT = "".join(_FAKE_STREAM_CHUNKS)


class TestChatHistory:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/chat/history")
        assert resp.status_code == 401

    async def test_fails_before_analysis_completes(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "chat-no-analysis@example.com")
        resp = await client.get("/chat/history", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ANALYSIS_NOT_COMPLETED"

    async def test_starts_empty_with_suggested_prompts(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "chat-empty@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        resp = await client.get("/chat/history", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["messages"] == []
        assert 2 <= len(body["suggested_prompts"]) <= 4


class TestSendMessage:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/chat/messages", json={"content": "Hello"})
        assert resp.status_code == 401

    async def test_fails_before_analysis_completes(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "chat-send-no-analysis@example.com")
        resp = await client.post("/chat/messages", headers=headers, json={"content": "Hello"})
        assert resp.status_code == 409

    async def test_empty_content_is_rejected(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "chat-empty-content@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        resp = await client.post("/chat/messages", headers=headers, json={"content": ""})
        assert resp.status_code == 422

    async def test_over_length_content_is_rejected(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "chat-long@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        resp = await client.post("/chat/messages", headers=headers, json={"content": "x" * 2001})
        assert resp.status_code == 422

    async def test_normal_question_streams_and_persists(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "chat-normal@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        # _complete_paid_analysis's own narrative-generation call(s) (plus a
        # fire-and-forget background retry race -- see analysis_service.
        # trigger_analysis's schedule_background_task) already move
        # call_count off zero before the chat call happens at all, so the
        # call this test cares about is asserted as a delta, not an
        # absolute count.
        baseline_calls = ai_recorder.call_count

        resp = await client.post("/chat/messages", headers=headers, json={"content": "What should I focus on?"})
        assert resp.status_code == 200
        assert resp.text == _EXPECTED_STREAMED_TEXT
        assert ai_recorder.call_count - baseline_calls == 1

        history = await client.get("/chat/history", headers=headers)
        messages = history.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What should I focus on?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == _EXPECTED_STREAMED_TEXT

    async def test_medical_question_is_refused_with_zero_ai_calls(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """Release-blocking: FR-019's hard refusal rule, verified as a real
        automated test, not manual spot-checking. Also proves BR-006 cost
        control -- a refused question never reaches the AI provider."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "chat-medical@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        baseline_calls = ai_recorder.call_count  # see test_normal_question_streams_and_persists

        resp = await client.post(
            "/chat/messages", headers=headers, json={"content": "Can I use minoxidil for my hair loss?"}
        )
        assert resp.status_code == 200
        assert "professional" in resp.text.lower()
        assert ai_recorder.call_count == baseline_calls

        history = await client.get("/chat/history", headers=headers)
        messages = history.json()["messages"]
        assert len(messages) == 2
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == resp.text

    async def test_repeated_calls_reuse_the_same_conversation(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "chat-reuse@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        await client.post("/chat/messages", headers=headers, json={"content": "First question"})
        await client.post("/chat/messages", headers=headers, json={"content": "Second question"})

        count = await db.execute(select(func.count()).select_from(Conversation))
        assert count.scalar_one() == 1

        history = await client.get("/chat/history", headers=headers)
        assert len(history.json()["messages"]) == 4
