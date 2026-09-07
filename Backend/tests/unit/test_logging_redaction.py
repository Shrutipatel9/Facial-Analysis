from app.core.logging import REDACTED, redact


class TestRedaction:
    def test_redacts_password_json_style(self):
        text = '{"email": "a@example.com", "password": "hunter2"}'
        assert "hunter2" not in redact(text)
        assert REDACTED in redact(text)

    def test_redacts_otp(self):
        text = "otp=123456 for user"
        result = redact(text)
        assert "123456" not in result

    def test_redacts_authorization_header_style(self):
        text = "Authorization: Bearer eyJhbGciOi.abc.def"
        result = redact(text)
        assert "eyJhbGciOi" not in result

    def test_leaves_unrelated_text_untouched(self):
        text = "User a@example.com logged in successfully"
        assert redact(text) == text
