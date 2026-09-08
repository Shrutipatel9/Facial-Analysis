from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_purpose_token,
    decode_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_otp_code,
    hash_password,
    hash_refresh_token,
    hash_reset_binding,
    verify_otp_code,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        h = hash_password("correcthorse9")
        assert verify_password("correcthorse9", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("correcthorse9")
        assert verify_password("wrong-password-1", h) is False

    def test_argon2_does_not_truncate_long_passwords(self):
        """Regression guard for the bcrypt-rejection decision
        (docs/security.md §7): bcrypt silently truncates at 72 bytes, so two
        passwords differing only after byte 72 would incorrectly verify as
        equal. Argon2 (via pwdlib) must not have this behavior."""
        base = "a" * 100
        password_a = base + "TAIL-ONE"
        password_b = base + "TAIL-TWO"

        h = hash_password(password_a)

        assert verify_password(password_a, h) is True
        assert verify_password(password_b, h) is False


class TestOTP:
    def test_generated_code_is_six_digits(self):
        code = generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_hash_and_verify_roundtrip(self):
        code = generate_otp_code()
        h = hash_otp_code(code)
        assert verify_otp_code(code, h) is True

    def test_tampered_code_is_rejected(self):
        code = "123456"
        h = hash_otp_code(code)
        assert verify_otp_code("654321", h) is False


class TestRefreshTokenPrimitives:
    def test_tokens_are_unique(self):
        assert generate_refresh_token() != generate_refresh_token()

    def test_hash_is_deterministic(self):
        token = generate_refresh_token()
        assert hash_refresh_token(token) == hash_refresh_token(token)

    def test_different_tokens_hash_differently(self):
        assert hash_refresh_token(generate_refresh_token()) != hash_refresh_token(generate_refresh_token())


class TestAccessToken:
    def test_roundtrip(self):
        token = create_access_token(subject="user-123", role="user")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "user"

    def test_carries_access_purpose_claim(self):
        """get_current_user (app/api/deps.py) rejects any token whose
        purpose isn't "access" -- an access token must always carry it."""
        token = create_access_token(subject="user-123", role="user")
        payload = decode_access_token(token)
        assert payload["purpose"] == "access"

    def test_expired_token_is_rejected(self):
        token = create_access_token(subject="user-123", role="user", expires_delta=timedelta(seconds=-1))
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_tampered_signature_is_rejected(self):
        token = create_access_token(subject="user-123", role="user")
        tampered = token[:-4] + ("A" if token[-4] != "A" else "B") + token[-3:]
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(tampered)

    def test_alg_none_token_is_rejected(self):
        """decode_access_token pins algorithms=["HS256"] explicitly rather
        than trusting the token's own `alg` header -- a token crafted with
        alg="none" (a classic algorithm-confusion attack) must be rejected,
        not accepted as an unsigned-but-valid token."""
        forged = jwt.encode({"sub": "user-123", "role": "admin"}, key=None, algorithm="none")
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(forged)

    def test_wrong_secret_token_is_rejected(self):
        forged = jwt.encode({"sub": "user-123", "role": "admin"}, "wrong-secret", algorithm="HS256")
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(forged)


class TestPurposeToken:
    def test_roundtrip(self):
        token = create_purpose_token(
            subject="user-123", purpose="password_reset", expires_delta=timedelta(minutes=10), pwd_fp="abc123"
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["purpose"] == "password_reset"
        assert payload["pwd_fp"] == "abc123"

    def test_expired_purpose_token_is_rejected(self):
        token = create_purpose_token(
            subject="user-123", purpose="password_reset", expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)


class TestResetBinding:
    def test_deterministic(self):
        assert hash_reset_binding("some-hash") == hash_reset_binding("some-hash")

    def test_changes_when_password_hash_changes(self):
        """The whole single-use mechanism for reset_token relies on this --
        a reset happening once must change the fingerprint so the same
        token can never be redeemed a second time."""
        assert hash_reset_binding("hash-before-reset") != hash_reset_binding("hash-after-reset")
