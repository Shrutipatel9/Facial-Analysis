import pytest
from httpx import AsyncClient

from tests.integration.test_report_flow import _auth_headers_and_user_id

pytestmark = pytest.mark.asyncio


class TestSubmitSupportRequest:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/support/requests", json={"subject": "Hi", "message": "Question."})
        assert resp.status_code == 401

    async def test_succeeds_and_relays_via_configured_console_sender(
        self, client: AsyncClient, email_sender, caplog, monkeypatch
    ):
        """EMAIL_PROVIDER=console (this project's test default) logs the
        relay instead of sending real email -- see ConsoleEmailSender."""
        from app.core.config import get_settings

        monkeypatch.setenv("SUPPORT_EMAIL", "care-team@example.com")
        get_settings.cache_clear()
        try:
            headers, _ = await _auth_headers_and_user_id(client, email_sender, "support-ok@example.com")

            import logging

            with caplog.at_level(logging.INFO, logger="app.services.email_service"):
                resp = await client.post(
                    "/support/requests",
                    headers=headers,
                    json={"subject": "Question about my report", "message": "Why is my jaw score low?"},
                )

            assert resp.status_code == 200, resp.text
            assert resp.json()["message"]
            assert any("Support request" in record.message for record in caplog.records)
            assert any("support-ok@example.com" in record.message for record in caplog.records)
        finally:
            monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
            get_settings.cache_clear()

    async def test_report_id_is_optional(self, client: AsyncClient, email_sender, monkeypatch):
        from app.core.config import get_settings

        monkeypatch.setenv("SUPPORT_EMAIL", "care-team@example.com")
        get_settings.cache_clear()
        try:
            headers, _ = await _auth_headers_and_user_id(client, email_sender, "support-no-report@example.com")
            resp = await client.post(
                "/support/requests", headers=headers, json={"subject": "General", "message": "Just a question."}
            )
            assert resp.status_code == 200, resp.text
        finally:
            monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
            get_settings.cache_clear()

    async def test_missing_subject_is_rejected(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "support-no-subject@example.com")
        resp = await client.post("/support/requests", headers=headers, json={"subject": "", "message": "Hello."})
        assert resp.status_code == 422

    async def test_oversized_message_is_rejected(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "support-too-long@example.com")
        resp = await client.post(
            "/support/requests", headers=headers, json={"subject": "Hi", "message": "x" * 5001}
        )
        assert resp.status_code == 422

    async def test_missing_support_email_config_returns_502(self, client: AsyncClient, email_sender, monkeypatch):
        from app.core.config import get_settings

        monkeypatch.setenv("SUPPORT_EMAIL", "")
        get_settings.cache_clear()
        try:
            headers, _ = await _auth_headers_and_user_id(client, email_sender, "support-unconfigured@example.com")
            resp = await client.post(
                "/support/requests", headers=headers, json={"subject": "Hi", "message": "Hello."}
            )
            assert resp.status_code == 502
            assert resp.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"
        finally:
            monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
            get_settings.cache_clear()
