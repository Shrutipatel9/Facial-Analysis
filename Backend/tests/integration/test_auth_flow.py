import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.otp_record import OTPRecord
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import jwt_service

pytestmark = pytest.mark.asyncio


async def _expire_cooldown_for(email: str) -> None:
    """Push the user's most recent OTP record's created_at far enough into
    the past that the resend cooldown no longer applies -- lets a test
    issue a second, independent OTP request without actually waiting."""
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        record_result = await session.execute(
            select(OTPRecord).where(OTPRecord.user_id == user.id).order_by(OTPRecord.created_at.desc()).limit(1)
        )
        record = record_result.scalar_one()
        record.created_at = datetime.now(UTC) - timedelta(minutes=5)
        await session.commit()


async def _register_and_verify(client: AsyncClient, email_sender, email: str) -> dict:
    """Full happy-path signup, returning the /auth/otp/verify JSON body.

    The refresh token is never in that body (v1.4) -- it arrives as an
    httpOnly Set-Cookie on this same response and is now sitting in
    `client.cookies`, which httpx automatically resends on every subsequent
    request through this same `client`. Callers that need the raw value
    (cross-session tests, tamper tests) read it via `client.cookies.get(
    "refresh_token")` right after this call, before any further request
    through the client rotates it.
    """
    resp = await client.post("/auth/register", json={"email": email, "password": "correcthorse9"})
    assert resp.status_code == 201, resp.text
    challenge_id = resp.json()["challenge_id"]
    otp = email_sender.sent[email]

    resp = await client.post("/auth/otp/verify", json={"challenge_id": challenge_id, "otp": otp})
    assert resp.status_code == 200, resp.text
    assert "refresh_token" in resp.cookies
    return resp.json()


class TestRegisterAndLoginHappyPath:
    async def test_signup_then_login(self, client: AsyncClient, email_sender):
        tokens = await _register_and_verify(client, email_sender, "signup@example.com")
        assert tokens["user"]["verification_status"] == "verified"
        assert tokens["user"]["role"] == "user"
        assert tokens["access_token"]
        assert "refresh_token" not in tokens  # cookie-only transport, never in the body

        resp = await client.post("/auth/login", json={"email": "signup@example.com", "password": "correcthorse9"})
        assert resp.status_code == 200
        assert resp.json()["purpose"] == "login"

        login_otp = email_sender.sent["signup@example.com"]
        resp = await client.post(
            "/auth/otp/verify", json={"challenge_id": resp.json()["challenge_id"], "otp": login_otp}
        )
        assert resp.status_code == 200


class TestRefreshCookieAndMe:
    """v1.4: refresh token moved from the Zustand store to an httpOnly
    cookie, and a fresh access token alone isn't enough to rehydrate the
    frontend's user object after a reload -- GET /auth/me covers that."""

    async def test_refresh_cookie_is_httponly_and_response_bodies_never_carry_it(
        self, client: AsyncClient, email_sender
    ):
        tokens = await _register_and_verify(client, email_sender, "cookieshape@example.com")
        assert "refresh_token" not in tokens

        resp = await client.post("/auth/refresh")
        assert "refresh_token" not in resp.json()
        assert "user" in resp.json()
        set_cookie_header = resp.headers.get("set-cookie")
        assert set_cookie_header is not None
        lowered = set_cookie_header.lower()
        assert "httponly" in lowered
        assert "samesite=strict" in lowered

    async def test_me_returns_current_user_with_valid_access_token(self, client: AsyncClient, email_sender):
        tokens = await _register_and_verify(client, email_sender, "meendpoint@example.com")
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "meendpoint@example.com"

    async def test_me_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_full_reload_recovery_via_cookie_refresh_then_me(self, client: AsyncClient, email_sender):
        """Simulates AuthHydrator's exact sequence on a fresh page load: no
        access token in memory, only whatever cookie the browser kept."""
        await _register_and_verify(client, email_sender, "reloadrecovery@example.com")

        refresh_resp = await client.post("/auth/refresh")
        assert refresh_resp.status_code == 200
        fresh_access_token = refresh_resp.json()["access_token"]

        me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {fresh_access_token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "reloadrecovery@example.com"


class TestRegistrationEdgeCases:
    async def test_duplicate_signup_on_verified_email_is_409(self, client: AsyncClient, email_sender):
        await _register_and_verify(client, email_sender, "verified@example.com")
        resp = await client.post(
            "/auth/register", json={"email": "verified@example.com", "password": "correcthorse9"}
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

    async def test_duplicate_signup_while_first_otp_still_pending_is_cooldown_429(
        self, client: AsyncClient, email_sender
    ):
        resp1 = await client.post(
            "/auth/register", json={"email": "duplicate-fast@example.com", "password": "correcthorse9"}
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/auth/register", json={"email": "duplicate-fast@example.com", "password": "anotherpass9"}
        )
        assert resp2.status_code == 429
        assert resp2.json()["error"]["code"] == "OTP_COOLDOWN"

    async def test_duplicate_signup_on_unverified_email_after_cooldown_is_treated_as_retry(
        self, client: AsyncClient, email_sender
    ):
        resp1 = await client.post(
            "/auth/register", json={"email": "pending@example.com", "password": "correcthorse9"}
        )
        assert resp1.status_code == 201
        await _expire_cooldown_for("pending@example.com")

        # Second attempt with a DIFFERENT password, once the cooldown has passed.
        resp2 = await client.post(
            "/auth/register", json={"email": "pending@example.com", "password": "anotherpass9"}
        )
        assert resp2.status_code == 201
        assert resp2.json()["challenge_id"] != resp1.json()["challenge_id"]

        # The old challenge_id must now be stale (superseded), not usable.
        stale_otp = email_sender.sent["pending@example.com"]
        resp = await client.post(
            "/auth/otp/verify", json={"challenge_id": resp1.json()["challenge_id"], "otp": stale_otp}
        )
        assert resp.status_code == 404

    async def test_login_on_unverified_account_routes_to_signup_purpose(self, client: AsyncClient, email_sender):
        resp = await client.post(
            "/auth/register", json={"email": "half-signed-up@example.com", "password": "correcthorse9"}
        )
        assert resp.status_code == 201
        await _expire_cooldown_for("half-signed-up@example.com")

        resp = await client.post(
            "/auth/login", json={"email": "half-signed-up@example.com", "password": "correcthorse9"}
        )
        assert resp.status_code == 200
        assert resp.json()["purpose"] == "signup"

    async def test_weak_password_rejected_at_schema_layer(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={"email": "weak@example.com", "password": "abc"})
        assert resp.status_code == 422


class TestLoginEdgeCases:
    async def test_wrong_password_is_generic_401(self, client: AsyncClient, email_sender):
        await _register_and_verify(client, email_sender, "haspassword@example.com")
        resp = await client.post(
            "/auth/login", json={"email": "haspassword@example.com", "password": "wrong-password-1"}
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_nonexistent_email_returns_same_generic_error_as_wrong_password(self, client: AsyncClient):
        """Anti-enumeration: a nonexistent email must not be distinguishable
        from a wrong password by response shape."""
        resp = await client.post(
            "/auth/login", json={"email": "nobody-here@example.com", "password": "whatever123"}
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


class TestOTPVerification:
    async def test_wrong_otp_increments_attempts_without_locking_before_the_fifth(
        self, client: AsyncClient, email_sender
    ):
        resp = await client.post("/auth/register", json={"email": "wrongotp@example.com", "password": "correcthorse9"})
        challenge_id = resp.json()["challenge_id"]

        for _ in range(4):
            resp = await client.post("/auth/otp/verify", json={"challenge_id": challenge_id, "otp": "000000"})
            assert resp.status_code == 400
            assert resp.json()["error"]["code"] == "OTP_INVALID"

        # Correct code on the 5th (final) attempt should still work -- only
        # a 5th *wrong* attempt locks, not the 5th attempt in general.
        otp = email_sender.sent["wrongotp@example.com"]
        resp = await client.post("/auth/otp/verify", json={"challenge_id": challenge_id, "otp": otp})
        assert resp.status_code == 200

    async def test_fifth_wrong_attempt_locks_and_blocks_subsequent_correct_attempts(
        self, client: AsyncClient, email_sender
    ):
        resp = await client.post("/auth/register", json={"email": "lockme@example.com", "password": "correcthorse9"})
        challenge_id = resp.json()["challenge_id"]

        for _ in range(5):
            resp = await client.post("/auth/otp/verify", json={"challenge_id": challenge_id, "otp": "000000"})

        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "ACCOUNT_LOCKED"
        assert resp.json()["error"]["retry_after_seconds"] > 0

        # Even the CORRECT code must now be rejected -- locked, not "wrong".
        otp = email_sender.sent["lockme@example.com"]
        resp = await client.post("/auth/otp/verify", json={"challenge_id": challenge_id, "otp": otp})
        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "ACCOUNT_LOCKED"

    async def test_expired_otp_is_rejected_without_counting_as_an_attempt(
        self, client: AsyncClient, email_sender, db
    ):
        resp = await client.post("/auth/register", json={"email": "expiring@example.com", "password": "correcthorse9"})
        challenge_id = resp.json()["challenge_id"]

        # Force expiry deterministically rather than sleeping in the test.
        async with async_session_factory() as session:
            record = await session.get(OTPRecord, challenge_id)
            record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

        otp = email_sender.sent["expiring@example.com"]
        resp = await client.post("/auth/otp/verify", json={"challenge_id": challenge_id, "otp": otp})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "OTP_EXPIRED"

        async with async_session_factory() as session:
            record = await session.get(OTPRecord, challenge_id)
            assert record.attempt_count == 0

    async def test_malformed_challenge_id_does_not_500(self, client: AsyncClient):
        resp = await client.post("/auth/otp/verify", json={"challenge_id": "not-a-uuid", "otp": "123456"})
        assert resp.status_code == 422  # rejected by schema (uuid.UUID parsing), never reaches the service

    async def test_unknown_challenge_id_is_404(self, client: AsyncClient):
        resp = await client.post(
            "/auth/otp/verify",
            json={"challenge_id": "00000000-0000-0000-0000-000000000000", "otp": "123456"},
        )
        assert resp.status_code == 404


class TestOTPResend:
    async def test_resend_before_cooldown_is_429(self, client: AsyncClient, email_sender):
        resp = await client.post("/auth/register", json={"email": "cooldown@example.com", "password": "correcthorse9"})
        challenge_id = resp.json()["challenge_id"]

        resp = await client.post("/auth/otp/resend", json={"challenge_id": challenge_id})
        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "OTP_COOLDOWN"
        assert resp.json()["error"]["retry_after_seconds"] > 0

    async def test_resend_after_cooldown_supersedes_old_challenge(self, client: AsyncClient, email_sender, db):
        resp = await client.post("/auth/register", json={"email": "resend@example.com", "password": "correcthorse9"})
        old_challenge_id = resp.json()["challenge_id"]

        # Force the cooldown to have already elapsed.
        async with async_session_factory() as session:
            record = await session.get(OTPRecord, old_challenge_id)
            record.created_at = datetime.now(UTC) - timedelta(minutes=5)
            await session.commit()

        resp = await client.post("/auth/otp/resend", json={"challenge_id": old_challenge_id})
        assert resp.status_code == 200
        new_challenge_id = resp.json()["challenge_id"]
        assert new_challenge_id != old_challenge_id

        old_otp = email_sender.sent["resend@example.com"]  # stale value, superseded below
        # The OLD challenge_id must now 404, even with what was its own code.
        resp = await client.post("/auth/otp/verify", json={"challenge_id": old_challenge_id, "otp": old_otp})
        assert resp.status_code == 404

    async def test_resend_on_unknown_challenge_is_404(self, client: AsyncClient):
        resp = await client.post(
            "/auth/otp/resend", json={"challenge_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert resp.status_code == 404


class TestRefreshRotationAndReuseDetection:
    async def test_refresh_rotates_and_old_token_stops_working(self, client: AsyncClient, email_sender):
        await _register_and_verify(client, email_sender, "rotate@example.com")
        old_token = client.cookies.get("refresh_token")

        resp = await client.post("/auth/refresh")
        assert resp.status_code == 200
        assert "refresh_token" not in resp.json()  # cookie-only transport
        new_token = resp.cookies.get("refresh_token")
        assert new_token != old_token
        assert new_token  # the client's jar was updated from the Set-Cookie header

        # The rotated-out token itself is now dead. (Replaying it would also
        # trigger reuse-detection and kill the whole family, including the
        # new token -- that's exercised separately, in the reuse test below,
        # not here.)
        resp = await client.post("/auth/refresh", headers={"Cookie": f"refresh_token={old_token}"})
        assert resp.status_code == 401

    async def test_expired_refresh_token_is_expired_not_reuse(self, client: AsyncClient, email_sender, db):
        await _register_and_verify(client, email_sender, "expiredrefresh@example.com")

        async with async_session_factory() as session:
            result = await session.execute(select(RefreshToken).order_by(RefreshToken.issued_at.desc()).limit(1))
            record = result.scalar_one()
            record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

        resp = await client.post("/auth/refresh")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_EXPIRED"

    async def test_garbage_refresh_token_is_generic_401(self, client: AsyncClient):
        resp = await client.post("/auth/refresh", headers={"Cookie": "refresh_token=not-a-real-token"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_TOKEN"

    async def test_missing_refresh_cookie_is_generic_401(self, client: AsyncClient):
        resp = await client.post("/auth/refresh")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_TOKEN"

    async def test_reuse_of_rotated_out_token_revokes_entire_family(self, client: AsyncClient, email_sender):
        """The single highest-priority test in this suite (docs/authentication.md).

        Sequence: issue token A -> refresh with A (get B, A now revoked) ->
        replay A again -> the ENTIRE family (including B) must now be dead.
        """
        await _register_and_verify(client, email_sender, "reuse@example.com")
        token_a = client.cookies.get("refresh_token")

        resp = await client.post("/auth/refresh")
        assert resp.status_code == 200
        token_b = resp.cookies.get("refresh_token")

        # Replay A (already rotated out) -- must be detected as reuse.
        resp = await client.post("/auth/refresh", headers={"Cookie": f"refresh_token={token_a}"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "SESSION_REVOKED"

        # B, though never itself reused, must ALSO now be dead -- the whole
        # family was revoked as a precaution.
        resp = await client.post("/auth/refresh", headers={"Cookie": f"refresh_token={token_b}"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "SESSION_REVOKED"

    async def test_concurrent_refresh_of_same_valid_token_has_exactly_one_winner(
        self, client: AsyncClient, email_sender
    ):
        """Distinct from the reuse test above: two requests race on the SAME
        still-valid token (e.g. two browser tabs firing a silent refresh at
        once). Exactly one must win; the loser must fail cleanly
        (RefreshTokenInvalidError) WITHOUT triggering a family revocation --
        both requests came from the legitimate client.

        Exercised at the service layer with two independent sessions. Plain
        asyncio.gather() timing isn't reliable enough to force the exact
        interleaving needed (both reads must complete before either update
        is attempted) -- a fast local DB round-trip can let one coroutine
        finish entirely before the other's first read even runs. An
        asyncio.Barrier, injected via rotate_refresh_token's test-only
        `_after_read_hook`, forces both coroutines to reach "read done" before
        either proceeds to the atomic update, deterministically reproducing
        the race rather than hoping the scheduler happens to interleave them.
        """
        await _register_and_verify(client, email_sender, "race@example.com")
        raw_refresh_token = client.cookies.get("refresh_token")
        barrier = asyncio.Barrier(2)

        async def _attempt() -> tuple[bool, str | None]:
            async with async_session_factory() as session:
                try:
                    result = await jwt_service.rotate_refresh_token(
                        session, raw_refresh_token, _after_read_hook=barrier.wait
                    )
                    await session.commit()
                    return True, result.refresh_token
                except Exception as exc:
                    await session.rollback()
                    return False, type(exc).__name__

        results = await asyncio.gather(_attempt(), _attempt())
        successes = [r for r in results if r[0]]
        failures = [r for r in results if not r[0]]

        assert len(successes) == 1, f"expected exactly one winner, got {results}"
        assert len(failures) == 1
        assert failures[0][1] == "RefreshTokenInvalidError"  # NOT RefreshTokenReuseError

        # And the family must still be alive: the winner's new token works.
        winning_new_token = successes[0][1]
        async with async_session_factory() as session:
            follow_up = await jwt_service.rotate_refresh_token(session, winning_new_token)
            await session.commit()
        assert follow_up.access_token


class TestLogout:
    async def test_logout_revokes_only_current_session(self, client: AsyncClient, email_sender):
        tokens = await _register_and_verify(client, email_sender, "logout@example.com")
        this_session_token = client.cookies.get("refresh_token")

        # A second, independent session for the same user (e.g. another
        # device) -- issued directly via the service layer for test setup.
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == "logout@example.com"))
            user = result.scalar_one()
            other_session_tokens = await jwt_service.issue_token_pair(session, user)
            await session.commit()

        resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert resp.status_code == 200
        # The cookie must be cleared on the response too, not just revoked
        # server-side -- otherwise the browser would keep resending a dead
        # token on every subsequent request.
        assert not resp.cookies.get("refresh_token")

        # The logged-out session's refresh token is now dead...
        resp = await client.post("/auth/refresh", headers={"Cookie": f"refresh_token={this_session_token}"})
        assert resp.status_code == 401

        # ...but the OTHER session is untouched (single-session logout scope).
        resp = await client.post(
            "/auth/refresh", headers={"Cookie": f"refresh_token={other_session_tokens.refresh_token}"}
        )
        assert resp.status_code == 200

    async def test_logout_is_idempotent_on_unknown_token(self, client: AsyncClient, email_sender):
        tokens = await _register_and_verify(client, email_sender, "idempotentlogout@example.com")
        resp = await client.post(
            "/auth/logout",
            headers={
                "Cookie": "refresh_token=already-gone-or-never-existed",
                "Authorization": f"Bearer {tokens['access_token']}",
            },
        )
        assert resp.status_code == 200

    async def test_logout_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/auth/logout", headers={"Cookie": "refresh_token=whatever"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"


class TestForgotPassword:
    async def test_nonexistent_email_gets_same_generic_response_as_real_one(
        self, client: AsyncClient, email_sender
    ):
        """Anti-enumeration: a forgot-password request for an email that
        doesn't exist must be indistinguishable from one that does."""
        await _register_and_verify(client, email_sender, "reset-real@example.com")

        real_resp = await client.post("/auth/forgot-password", json={"email": "reset-real@example.com"})
        fake_resp = await client.post("/auth/forgot-password", json={"email": "reset-nobody@example.com"})

        assert real_resp.status_code == fake_resp.status_code == 200
        assert real_resp.json() == fake_resp.json()
        # And no email is actually sent for the nonexistent account.
        assert "reset-nobody@example.com" not in email_sender.sent

    async def test_repeated_request_for_real_account_stays_generic_but_cooldown_still_applies(
        self, client: AsyncClient, email_sender
    ):
        """The per-account OTP cooldown still functions (no second email
        while on cooldown) -- it just must never surface as a different
        HTTP status/body than the always-200 generic response, or sending
        the same request twice would itself become an enumeration signal."""
        await _register_and_verify(client, email_sender, "reset-cooldown@example.com")

        first = await client.post("/auth/forgot-password", json={"email": "reset-cooldown@example.com"})
        assert first.status_code == 200
        first_otp = email_sender.sent["reset-cooldown@example.com"]

        second = await client.post("/auth/forgot-password", json={"email": "reset-cooldown@example.com"})
        assert second.status_code == 200
        assert second.json() == first.json()
        # Still on cooldown server-side -- no new code was actually issued.
        assert email_sender.sent["reset-cooldown@example.com"] == first_otp

    async def test_reset_with_correct_code_changes_password_and_revokes_every_session(
        self, client: AsyncClient, email_sender
    ):
        await _register_and_verify(client, email_sender, "reset-success@example.com")
        this_session_token = client.cookies.get("refresh_token")

        # A second, independent session (e.g. another device), like the
        # logout test does -- both must die once the password is reset.
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == "reset-success@example.com"))
            user = result.scalar_one()
            other_session_tokens = await jwt_service.issue_token_pair(session, user)
            await session.commit()

        await client.post("/auth/forgot-password", json={"email": "reset-success@example.com"})
        otp = email_sender.sent["reset-success@example.com"]

        verify_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-success@example.com", "otp": otp}
        )
        assert verify_resp.status_code == 200, verify_resp.text
        reset_token = verify_resp.json()["reset_token"]

        resp = await client.post(
            "/auth/reset-password", json={"reset_token": reset_token, "new_password": "brandnewpass9"}
        )
        assert resp.status_code == 200, resp.text

        # Old password no longer works.
        resp = await client.post(
            "/auth/login", json={"email": "reset-success@example.com", "password": "correcthorse9"}
        )
        assert resp.status_code == 401

        # New password does.
        resp = await client.post(
            "/auth/login", json={"email": "reset-success@example.com", "password": "brandnewpass9"}
        )
        assert resp.status_code == 200

        # Both pre-reset sessions are dead, not just one.
        resp = await client.post("/auth/refresh", headers={"Cookie": f"refresh_token={this_session_token}"})
        assert resp.status_code == 401
        resp = await client.post(
            "/auth/refresh", headers={"Cookie": f"refresh_token={other_session_tokens.refresh_token}"}
        )
        assert resp.status_code == 401

    async def test_reset_token_cannot_be_reused_after_success(self, client: AsyncClient, email_sender):
        """Single-use, enforced via the password-hash-fingerprint claim --
        the same reset_token must not be able to reset the password twice."""
        await _register_and_verify(client, email_sender, "reset-reuse@example.com")
        await client.post("/auth/forgot-password", json={"email": "reset-reuse@example.com"})
        otp = email_sender.sent["reset-reuse@example.com"]

        verify_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-reuse@example.com", "otp": otp}
        )
        reset_token = verify_resp.json()["reset_token"]

        first = await client.post(
            "/auth/reset-password", json={"reset_token": reset_token, "new_password": "brandnewpass9"}
        )
        assert first.status_code == 200

        second = await client.post(
            "/auth/reset-password", json={"reset_token": reset_token, "new_password": "anothernewpass9"}
        )
        assert second.status_code == 400
        assert second.json()["error"]["code"] == "RESET_TOKEN_INVALID"

    async def test_expired_reset_token_rejected(self, client: AsyncClient, email_sender):
        settings = get_settings()
        expired_token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "purpose": "password_reset",
                "pwd_fp": "irrelevant",
                "exp": datetime.now(UTC) - timedelta(seconds=1),
                "iat": datetime.now(UTC) - timedelta(minutes=20),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        resp = await client.post(
            "/auth/reset-password", json={"reset_token": expired_token, "new_password": "brandnewpass9"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "RESET_TOKEN_INVALID"

    async def test_reset_token_with_wrong_purpose_claim_rejected(self, client: AsyncClient, email_sender):
        """A token minted for a different purpose (even a real access token)
        must never work as a password-reset credential."""
        await _register_and_verify(client, email_sender, "reset-wrongpurpose@example.com")
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == "reset-wrongpurpose@example.com"))
            user = result.scalar_one()
            tokens = await jwt_service.issue_token_pair(session, user)
            await session.commit()

        resp = await client.post(
            "/auth/reset-password",
            json={"reset_token": tokens.access_token, "new_password": "brandnewpass9"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "RESET_TOKEN_INVALID"

    async def test_reset_token_cannot_be_used_as_bearer_access_token(self, client: AsyncClient, email_sender):
        """Regression test for the get_current_user purpose-claim hardening:
        a valid reset_token must never authenticate a protected endpoint."""
        await _register_and_verify(client, email_sender, "reset-notbearer@example.com")
        await client.post("/auth/forgot-password", json={"email": "reset-notbearer@example.com"})
        otp = email_sender.sent["reset-notbearer@example.com"]

        verify_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-notbearer@example.com", "otp": otp}
        )
        reset_token = verify_resp.json()["reset_token"]

        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {reset_token}"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_reset_rejects_new_password_same_as_current(self, client: AsyncClient, email_sender):
        await _register_and_verify(client, email_sender, "reset-samepass@example.com")
        await client.post("/auth/forgot-password", json={"email": "reset-samepass@example.com"})
        otp = email_sender.sent["reset-samepass@example.com"]

        verify_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-samepass@example.com", "otp": otp}
        )
        reset_token = verify_resp.json()["reset_token"]

        resp = await client.post(
            "/auth/reset-password", json={"reset_token": reset_token, "new_password": "correcthorse9"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SAME_PASSWORD"

    async def test_reset_with_wrong_code_is_generic_regardless_of_account_existence(
        self, client: AsyncClient, email_sender
    ):
        await _register_and_verify(client, email_sender, "reset-wrongcode@example.com")
        await client.post("/auth/forgot-password", json={"email": "reset-wrongcode@example.com"})

        real_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-wrongcode@example.com", "otp": "000000"}
        )
        fake_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-neverexisted@example.com", "otp": "000000"}
        )
        assert real_resp.status_code == fake_resp.status_code == 400
        assert real_resp.json()["error"]["code"] == fake_resp.json()["error"]["code"] == "OTP_INVALID"

    async def test_reset_without_any_pending_request_is_generic_invalid(self, client: AsyncClient, email_sender):
        """An existing, verified account that never called forgot-password
        must fail the same generic way as a wrong code -- not a distinct
        "no reset pending" error that would leak account state."""
        await _register_and_verify(client, email_sender, "reset-nopending@example.com")

        resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-nopending@example.com", "otp": "123456"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "OTP_INVALID"

    async def test_reset_with_expired_code(self, client: AsyncClient, email_sender):
        await _register_and_verify(client, email_sender, "reset-expired@example.com")
        await client.post("/auth/forgot-password", json={"email": "reset-expired@example.com"})
        otp = email_sender.sent["reset-expired@example.com"]

        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == "reset-expired@example.com"))
            user = result.scalar_one()
            record_result = await session.execute(
                select(OTPRecord).where(OTPRecord.user_id == user.id).order_by(OTPRecord.created_at.desc()).limit(1)
            )
            record = record_result.scalar_one()
            record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

        resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-expired@example.com", "otp": otp}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "OTP_EXPIRED"

    async def test_five_wrong_attempts_locks_reset_too(self, client: AsyncClient, email_sender):
        """Lockout is shared across every OTP purpose for a given account
        (signup/login/reset alike) -- five wrong reset attempts lock the
        account exactly like five wrong signup/login attempts would."""
        await _register_and_verify(client, email_sender, "reset-lockout@example.com")
        await client.post("/auth/forgot-password", json={"email": "reset-lockout@example.com"})

        for _ in range(5):
            resp = await client.post(
                "/auth/reset-password/verify", json={"email": "reset-lockout@example.com", "otp": "000000"}
            )

        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "ACCOUNT_LOCKED"

        # Locked out of ordinary login too, not just reset -- same
        # otp_locked_until field. request_otp (which login also calls, to
        # issue its own OTP challenge) checks the lockout before it will
        # generate anything, so login itself is blocked at 429, not just
        # some later OTP-verify step.
        resp = await client.post(
            "/auth/login", json={"email": "reset-lockout@example.com", "password": "correcthorse9"}
        )
        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "ACCOUNT_LOCKED"

    async def test_weak_new_password_rejected_at_schema_layer(self, client: AsyncClient, email_sender):
        await _register_and_verify(client, email_sender, "reset-weak@example.com")
        await client.post("/auth/forgot-password", json={"email": "reset-weak@example.com"})
        otp = email_sender.sent["reset-weak@example.com"]

        verify_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "reset-weak@example.com", "otp": otp}
        )
        reset_token = verify_resp.json()["reset_token"]

        resp = await client.post(
            "/auth/reset-password", json={"reset_token": reset_token, "new_password": "abc"}
        )
        assert resp.status_code == 422

    async def test_new_password_same_as_email_local_part_rejected_at_service_layer(
        self, client: AsyncClient, email_sender
    ):
        """This rule can only be enforced once reset_token is decoded and
        the user's real email is known -- unlike registration, the schema
        layer alone (no email in the request) can't catch it, so it must
        surface as WEAK_PASSWORD from the service layer instead of 422 at
        the schema layer."""
        await _register_and_verify(client, email_sender, "resetemail9@example.com")
        await client.post("/auth/forgot-password", json={"email": "resetemail9@example.com"})
        otp = email_sender.sent["resetemail9@example.com"]

        verify_resp = await client.post(
            "/auth/reset-password/verify", json={"email": "resetemail9@example.com", "otp": otp}
        )
        reset_token = verify_resp.json()["reset_token"]

        resp = await client.post(
            "/auth/reset-password", json={"reset_token": reset_token, "new_password": "resetemail9"}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "WEAK_PASSWORD"
