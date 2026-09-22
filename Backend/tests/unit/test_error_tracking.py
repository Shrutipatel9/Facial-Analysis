from types import SimpleNamespace

from app.core.error_tracking import _redact_event_strings, init_error_tracking


class TestInitErrorTracking:
    def test_is_a_no_op_without_a_dsn(self, monkeypatch):
        """Default posture (no SENTRY_DSN configured, tests included) --
        must never call sentry_sdk.init at all."""
        calls: list[dict] = []
        monkeypatch.setattr("app.core.error_tracking.sentry_sdk.init", lambda **kwargs: calls.append(kwargs))
        monkeypatch.setattr(
            "app.core.error_tracking.get_settings",
            lambda: SimpleNamespace(sentry_dsn=None, environment="test"),
        )
        init_error_tracking()
        assert calls == []

    def test_initializes_when_a_dsn_is_configured(self, monkeypatch):
        calls: list[dict] = []
        monkeypatch.setattr("app.core.error_tracking.sentry_sdk.init", lambda **kwargs: calls.append(kwargs))
        monkeypatch.setattr(
            "app.core.error_tracking.get_settings",
            lambda: SimpleNamespace(sentry_dsn="https://fake@example.ingest.sentry.io/1", environment="production"),
        )
        init_error_tracking()
        assert len(calls) == 1
        assert calls[0]["dsn"] == "https://fake@example.ingest.sentry.io/1"
        assert calls[0]["send_default_pii"] is False
        assert calls[0]["before_send"] is _redact_event_strings


class TestRedactEventStrings:
    def test_redacts_the_top_level_message(self):
        event = {"message": 'login failed: {"password": "hunter2"}'}
        result = _redact_event_strings(event, {})
        assert "hunter2" not in result["message"]

    def test_redacts_exception_values(self):
        event = {"exception": {"values": [{"type": "ValueError", "value": "bad otp=123456"}]}}
        result = _redact_event_strings(event, {})
        assert "123456" not in result["exception"]["values"][0]["value"]

    def test_redacts_breadcrumb_messages(self):
        event = {"breadcrumbs": {"values": [{"message": "token=abc123secret"}]}}
        result = _redact_event_strings(event, {})
        assert "abc123secret" not in result["breadcrumbs"]["values"][0]["message"]

    def test_leaves_an_event_with_no_sensitive_fields_untouched(self):
        event = {"message": "user logged in", "exception": {"values": []}}
        result = _redact_event_strings(event, {})
        assert result["message"] == "user logged in"
