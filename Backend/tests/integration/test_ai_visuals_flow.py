"""Integration tests for the AI Visuals endpoints (FR-020, Milestone 2
Phase 11). No real Gemini key is configured in tests (BR-006 -- real calls
never run in CI), so generation always ends in "failed" here; these tests
cover the endpoint contract, not real generation quality -- same posture as
tests/integration/test_report_flow.py's TestReportFeatureVisual class,
whose setup helpers this file reuses directly."""

import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_visual import AiVisual
from tests.integration.test_report_flow import _auth_headers_and_user_id, _complete_paid_analysis

# `ai_recorder` (used by parameter name below) is a project-wide conftest.py
# fixture, resolved by pytest without an import.

pytestmark = pytest.mark.asyncio


def _select_visuals(user_id: uuid.UUID, kind: str):
    return select(AiVisual).where(AiVisual.user_id == user_id, AiVisual.kind == kind)


async def _wait_for_all_terminal(db: AsyncSession, user_id: uuid.UUID, kind: str, timeout: float = 5.0) -> None:
    """Polls until every row for (user_id, kind) has left pending/generating.
    populate_existing avoids the identity-map staleness that made
    test_report_flow.py's equivalent helper flaky before it used the same
    fix -- see that file's _wait_for_all_visuals_terminal docstring."""
    deadline = asyncio.get_event_loop().time() + timeout
    terminal = {"generated", "failed"}
    while asyncio.get_event_loop().time() < deadline:
        result = await db.execute(_select_visuals(user_id, kind).execution_options(populate_existing=True))
        rows = result.scalars().all()
        if rows and all(row.status in terminal for row in rows):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"visual generation did not settle within {timeout}s for {user_id}/{kind}")


class TestCreateVisuals:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/ai-visuals/hairstyle")
        assert resp.status_code == 401

    async def test_fails_before_analysis_completes(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "av-no-analysis@example.com")
        resp = await client.post("/ai-visuals/hairstyle", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ANALYSIS_NOT_COMPLETED"

    async def test_unknown_kind_is_rejected(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "av-bad-kind@example.com")
        resp = await client.post("/ai-visuals/nonsense", headers=headers)
        assert resp.status_code == 422

    async def test_hairstyle_creates_five_variations(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "av-hairstyle@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        resp = await client.post("/ai-visuals/hairstyle", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body) == 5
        assert all(entry["kind"] == "hairstyle" for entry in body)
        assert sum(1 for entry in body if entry["is_recommended"]) == 1
        assert all(entry["name"] for entry in body)
        assert all(entry["attributes"] for entry in body)

    async def test_aging_creates_three_fixed_steps(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "av-aging@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        resp = await client.post("/ai-visuals/aging", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body) == 3
        ages = [entry["attributes"]["age_years"] for entry in body]
        assert ages == [31, 33, 38]
        assert all(entry["is_recommended"] is False for entry in body)

    async def test_generation_is_triggered_exactly_once_per_kind(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """BR-006 cost control: a repeat POST (idempotent, get-or-create)
        must not re-insert or reset the variation rows."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "av-once@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        await client.post("/ai-visuals/outfit", headers=headers)
        await _wait_for_all_terminal(db, user_id, "outfit")

        first = await db.execute(_select_visuals(user_id, "outfit").execution_options(populate_existing=True))
        first_rows = {row.id: row.attempt_count for row in first.scalars().all()}

        await client.post("/ai-visuals/outfit", headers=headers)  # repeat, idempotent
        await asyncio.sleep(0.05)

        second = await db.execute(_select_visuals(user_id, "outfit").execution_options(populate_existing=True))
        second_rows = {row.id: row.attempt_count for row in second.scalars().all()}
        assert second_rows == first_rows  # unchanged -- no re-trigger, no duplicate rows


class TestListVisuals:
    async def test_returns_empty_before_creation(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "av-list-empty@example.com")
        resp = await client.get("/ai-visuals/hairstyle", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_reflects_created_variations(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "av-list@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        await client.post("/ai-visuals/hairstyle", headers=headers)

        resp = await client.get("/ai-visuals/hairstyle", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 5


class TestVisualImage:
    async def test_ungenerated_variation_is_404(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "av-image-404@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        created = await client.post("/ai-visuals/hairstyle", headers=headers)
        variation_id = created.json()[0]["id"]

        resp = await client.get(f"/ai-visuals/hairstyle/{variation_id}/image", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "AI_VISUAL_NOT_FOUND"

    async def test_unknown_variation_id_is_404(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "av-image-unknown@example.com")
        resp = await client.get(f"/ai-visuals/hairstyle/{uuid.uuid4()}/image", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "AI_VISUAL_NOT_FOUND"

    async def test_another_users_variation_is_404(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers_a, user_a = await _auth_headers_and_user_id(client, email_sender, "av-owner@example.com")
        await _complete_paid_analysis(client, headers_a, db, user_a)
        created = await client.post("/ai-visuals/hairstyle", headers=headers_a)
        variation_id = created.json()[0]["id"]

        headers_b, _ = await _auth_headers_and_user_id(client, email_sender, "av-not-owner@example.com")
        resp = await client.get(f"/ai-visuals/hairstyle/{variation_id}/image", headers=headers_b)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "AI_VISUAL_NOT_FOUND"
