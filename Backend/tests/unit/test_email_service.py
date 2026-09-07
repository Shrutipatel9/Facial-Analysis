from app.services.email_service import _build_otp_message


class TestBuildOtpMessage:
    def test_includes_code_and_recipient(self):
        message = _build_otp_message(
            from_addr="noreply@example.com", to_email="user@example.com", otp_code="123456", purpose="signup"
        )
        assert message["To"] == "user@example.com"
        assert message["From"] == "noreply@example.com"
        assert "123456" in message["Subject"]
        assert "123456" in message.get_content()

    def test_signup_and_login_purposes_have_distinct_copy(self):
        signup = _build_otp_message(
            from_addr="a@example.com", to_email="u@example.com", otp_code="111111", purpose="signup"
        )
        login = _build_otp_message(
            from_addr="a@example.com", to_email="u@example.com", otp_code="111111", purpose="login"
        )
        assert "account" in signup.get_content()
        assert "sign in" in login.get_content()
        assert signup.get_content() != login.get_content()

    def test_unknown_purpose_falls_back_gracefully(self):
        # Defensive: should never happen (purpose is always "signup" or
        # "login" in practice), but must not raise if it somehow did.
        message = _build_otp_message(
            from_addr="a@example.com", to_email="u@example.com", otp_code="222222", purpose="something-else"
        )
        assert "222222" in message.get_content()
