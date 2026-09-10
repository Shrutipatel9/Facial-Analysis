import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.photo import Photo
from app.models.photo_blob import PhotoBlob
from app.services.photo_service import is_photo_set_ready
from app.services.photo_validation_service import REQUIRED_ANGLES
from tests.integration.test_auth_flow import _register_and_verify

pytestmark = pytest.mark.asyncio

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "photos"


def _load(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


# Angle-appropriate fixtures for the pose_match check -- pass_all.jpg is a
# genuinely frontal photo; pass_right_3q.jpg/pass_left_3q.jpg are
# synthesized (asymmetric horizontal compression) from it to plausibly
# shift the nose/eye symmetry the way an actual 3/4 turn does. See
# photo_validation_service.py's estimate_yaw_ratio/classify_pose.
_FIXTURE_FOR_ANGLE = {
    "front": "pass_all.jpg",
    "right_3q": "pass_right_3q.jpg",
    "left_3q": "pass_left_3q.jpg",
}


async def _auth_headers(client: AsyncClient, email_sender, email: str) -> dict:
    tokens = await _register_and_verify(client, email_sender, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _upload(client: AsyncClient, headers: dict, angle: str, fixture: str, capture_method: str = "upload"):
    return await client.post(
        "/photos",
        headers=headers,
        data={"angle": angle, "capture_method": capture_method},
        files={"file": (fixture, _load(fixture), "image/jpeg")},
    )


class TestUploadPhoto:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post(
            "/photos",
            data={"angle": "front", "capture_method": "upload"},
            files={"file": ("pass_all.jpg", _load("pass_all.jpg"), "image/jpeg")},
        )
        assert resp.status_code == 401

    async def test_unknown_angle_is_rejected(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-badangle@example.com")
        resp = await _upload(client, headers, "back", "pass_all.jpg")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "PHOTO_ANGLE_UNKNOWN"

    async def test_unsupported_content_type_is_rejected(self, client: AsyncClient, email_sender):
        # DNG intentionally unsupported this pass -- see photo_service.py.
        headers = await _auth_headers(client, email_sender, "photo-badtype@example.com")
        resp = await client.post(
            "/photos",
            headers=headers,
            data={"angle": "front", "capture_method": "upload"},
            files={"file": ("photo.dng", b"not a real dng", "image/x-adobe-dng")},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "PHOTO_UPLOAD_INVALID"

    async def test_resolution_check_fails(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-res@example.com")
        resp = await _upload(client, headers, "front", "too_small.jpg")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["validation_status"] == "failed"
        check = next(c for c in body["checks"] if c["check"] == "resolution")
        assert check["passed"] is False

    async def test_brightness_check_fails(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-bright@example.com")
        resp = await _upload(client, headers, "front", "too_dark.jpg")
        body = resp.json()
        check = next(c for c in body["checks"] if c["check"] == "brightness")
        assert check["passed"] is False

    async def test_face_count_check_fails_no_face(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-noface@example.com")
        resp = await _upload(client, headers, "front", "no_face.jpg")
        body = resp.json()
        check = next(c for c in body["checks"] if c["check"] == "face_count")
        assert check["passed"] is False
        assert "No face" in check["reason"]

    async def test_face_count_check_fails_multiple_faces(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-multiface@example.com")
        resp = await _upload(client, headers, "front", "multi_face.jpg")
        body = resp.json()
        check = next(c for c in body["checks"] if c["check"] == "face_count")
        assert check["passed"] is False
        assert "one face" in check["reason"]

    async def test_frame_proportion_check_fails(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-frame@example.com")
        resp = await _upload(client, headers, "front", "tight_crop.jpg")
        body = resp.json()
        check = next(c for c in body["checks"] if c["check"] == "frame_proportion")
        assert check["passed"] is False

    async def test_pose_match_fails_front_photo_uploaded_as_side_angle(
        self, client: AsyncClient, email_sender
    ):
        """The literal bug this check exists for: a clearly frontal photo
        uploaded for a 3/4-turn angle slot must be rejected, not silently
        accepted as if it showed that angle."""
        headers = await _auth_headers(client, email_sender, "photo-pose-frontforside@example.com")
        resp = await _upload(client, headers, "right_3q", "pass_all.jpg")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["validation_status"] == "failed"
        check = next(c for c in body["checks"] if c["check"] == "pose_match")
        assert check["passed"] is False
        assert "right side" in check["reason"].lower()

    async def test_pose_match_fails_side_photo_uploaded_as_front_angle(
        self, client: AsyncClient, email_sender
    ):
        headers = await _auth_headers(client, email_sender, "photo-pose-sideforfront@example.com")
        resp = await _upload(client, headers, "front", "pass_right_3q.jpg")
        body = resp.json()
        assert body["validation_status"] == "failed"
        check = next(c for c in body["checks"] if c["check"] == "pose_match")
        assert check["passed"] is False

    async def test_pose_match_fails_left_and_right_swapped(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-pose-swapped@example.com")
        resp = await _upload(client, headers, "left_3q", "pass_right_3q.jpg")
        body = resp.json()
        assert body["validation_status"] == "failed"
        check = next(c for c in body["checks"] if c["check"] == "pose_match")
        assert check["passed"] is False

    async def test_pose_match_passes_when_angle_and_pose_agree(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-pose-agree@example.com")
        for angle_id, fixture in _FIXTURE_FOR_ANGLE.items():
            resp = await _upload(client, headers, angle_id, fixture)
            body = resp.json()
            check = next(c for c in body["checks"] if c["check"] == "pose_match")
            assert check["passed"] is True, f"{angle_id} unexpectedly failed pose_match: {check}"

    async def test_full_pass_marks_validation_status_passed(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-pass@example.com")
        resp = await _upload(client, headers, "front", "pass_all.jpg")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["validation_status"] == "passed"
        assert all(c["passed"] for c in body["checks"])
        assert {c["check"] for c in body["checks"]} == {
            "file_readable",
            "resolution",
            "brightness",
            "face_count",
            "frame_proportion",
            "occlusion",
            "pose_match",
        }
        assert body["angle"] == "front"
        assert body["capture_method"] == "upload"

    async def test_upsert_not_duplicate_on_retry(self, client: AsyncClient, email_sender, db):
        headers = await _auth_headers(client, email_sender, "photo-retry@example.com")
        first = await _upload(client, headers, "front", "too_small.jpg")
        first_id = first.json()["id"]

        second = await _upload(client, headers, "front", "pass_all.jpg")
        assert second.json()["id"] == first_id
        assert second.json()["validation_status"] == "passed"

        result = await db.execute(select(Photo).where(Photo.angle == "front"))
        assert len(result.scalars().all()) == 1


class TestPhotoStatusAndCompletion:
    async def test_status_reflects_per_angle_progress_and_completion(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-status@example.com")

        resp = await client.get("/photos/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["completed"] is False
        assert len(body["angles"]) == len(REQUIRED_ANGLES)
        assert all(a["photo"] is None for a in body["angles"])

        for angle in REQUIRED_ANGLES:
            resp = await _upload(client, headers, angle.id, _FIXTURE_FOR_ANGLE[angle.id])
            assert resp.status_code == 200, resp.text
            assert resp.json()["validation_status"] == "passed"

        resp = await client.get("/photos/status", headers=headers)
        body = resp.json()
        assert body["completed"] is True
        assert all(
            a["photo"] is not None and a["photo"]["validation_status"] == "passed" for a in body["angles"]
        )

    async def test_br004_is_photo_set_ready_false_on_partial_set(self, client: AsyncClient, email_sender, db):
        headers = await _auth_headers(client, email_sender, "photo-br004@example.com")
        me = await client.get("/auth/me", headers=headers)
        user_id = uuid.UUID(me.json()["id"])

        await _upload(client, headers, "front", "pass_all.jpg")
        assert await is_photo_set_ready(db, user_id) is False

        await _upload(client, headers, "left_3q", "pass_left_3q.jpg")
        await _upload(client, headers, "right_3q", "pass_right_3q.jpg")
        assert await is_photo_set_ready(db, user_id) is True

    async def test_identity_check_is_null_before_set_is_complete(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-identity-partial@example.com")
        resp = await client.get("/photos/status", headers=headers)
        assert resp.json()["identity_check"] is None

        await _upload(client, headers, "front", "pass_all.jpg")
        resp = await client.get("/photos/status", headers=headers)
        assert resp.json()["identity_check"] is None

    async def test_identity_check_is_consistent_for_the_same_person(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-identity-ok@example.com")
        for angle in REQUIRED_ANGLES:
            resp = await _upload(client, headers, angle.id, _FIXTURE_FOR_ANGLE[angle.id])
            assert resp.status_code == 200, resp.text

        resp = await client.get("/photos/status", headers=headers)
        identity_check = resp.json()["identity_check"]
        assert identity_check == {"consistent": True, "mismatched_angles": [], "message": None}

    async def test_identity_check_flags_a_different_person_and_names_it(
        self, client: AsyncClient, email_sender
    ):
        headers = await _auth_headers(client, email_sender, "photo-identity-mismatch@example.com")
        # front is a different, real person; right_3q/left_3q are the
        # correct angle-appropriate photos of the actual test identity --
        # each passes its OWN per-photo checks independently (BR-005 is
        # not what should catch this), only the cross-photo check should.
        resp = await _upload(client, headers, "front", "different_person.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"
        resp = await _upload(client, headers, "right_3q", "pass_right_3q.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"
        resp = await _upload(client, headers, "left_3q", "pass_left_3q.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"

        resp = await client.get("/photos/status", headers=headers)
        body = resp.json()
        # Every individual photo still shows as passed -- the mismatch is
        # a set-level signal, not a per-photo validation failure.
        assert body["completed"] is True
        assert all(a["photo"]["validation_status"] == "passed" for a in body["angles"])

        identity_check = body["identity_check"]
        assert identity_check["consistent"] is False
        assert identity_check["mismatched_angles"] == ["front"]
        assert identity_check["message"]

    async def test_identity_check_flags_a_different_person_for_right_3q_and_names_it(
        self, client: AsyncClient, email_sender
    ):
        # different_person_right_3q.jpg is an angle-appropriate synthesis
        # (asymmetric horizontal compression, same technique as
        # pass_right_3q.jpg itself) of different_person.jpg -- the plain
        # fixture only passes pose_match for "front", so this is needed to
        # exercise a right_3q mismatch through the real upload endpoint,
        # not just the pure check_photo_set_identity function.
        headers = await _auth_headers(client, email_sender, "photo-identity-mismatch-right@example.com")
        resp = await _upload(client, headers, "front", "pass_all.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"
        resp = await _upload(client, headers, "right_3q", "different_person_right_3q.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"
        resp = await _upload(client, headers, "left_3q", "pass_left_3q.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"

        resp = await client.get("/photos/status", headers=headers)
        identity_check = resp.json()["identity_check"]
        assert identity_check["consistent"] is False
        assert identity_check["mismatched_angles"] == ["right_3q"]

    async def test_identity_check_flags_a_different_person_for_left_3q_and_names_it(
        self, client: AsyncClient, email_sender
    ):
        headers = await _auth_headers(client, email_sender, "photo-identity-mismatch-left@example.com")
        resp = await _upload(client, headers, "front", "pass_all.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"
        resp = await _upload(client, headers, "right_3q", "pass_right_3q.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"
        resp = await _upload(client, headers, "left_3q", "different_person_left_3q.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"

        resp = await client.get("/photos/status", headers=headers)
        identity_check = resp.json()["identity_check"]
        assert identity_check["consistent"] is False
        assert identity_check["mismatched_angles"] == ["left_3q"]

    async def test_retake_clears_the_mismatch_and_does_not_duplicate_the_photo_row(
        self, client: AsyncClient, email_sender, db
    ):
        headers = await _auth_headers(client, email_sender, "photo-identity-retake@example.com")
        me = await client.get("/auth/me", headers=headers)
        user_id = uuid.UUID(me.json()["id"])

        resp = await _upload(client, headers, "front", "different_person.jpg")
        assert resp.status_code == 200, resp.text
        await _upload(client, headers, "right_3q", "pass_right_3q.jpg")
        await _upload(client, headers, "left_3q", "pass_left_3q.jpg")

        resp = await client.get("/photos/status", headers=headers)
        assert resp.json()["identity_check"]["mismatched_angles"] == ["front"]

        # Retake the flagged angle with the correct photo -- an upsert by
        # (user_id, angle), not a new row (BR-004/photo_service.upload_photo).
        resp = await _upload(client, headers, "front", "pass_all.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"

        resp = await client.get("/photos/status", headers=headers)
        identity_check = resp.json()["identity_check"]
        assert identity_check == {"consistent": True, "mismatched_angles": [], "message": None}

        rows = (await db.execute(select(Photo).where(Photo.user_id == user_id))).scalars().all()
        assert len(rows) == 3
        assert {row.angle for row in rows} == {"front", "right_3q", "left_3q"}

        # The retake replaced the same (user_id, angle) blob in place --
        # same content_type/extension means the same storage_reference key,
        # so this must be an update, not a second orphaned blob row.
        front_row = next(row for row in rows if row.angle == "front")
        blob = await db.get(PhotoBlob, front_row.storage_reference)
        assert blob is not None
        assert blob.content == _load("pass_all.jpg")
        stale_blob_count = (
            await db.execute(
                select(PhotoBlob).where(PhotoBlob.id.like(f"{user_id}/front%"))
            )
        ).scalars().all()
        assert len(stale_blob_count) == 1

    async def test_retaking_a_consistent_set_with_a_mismatched_photo_introduces_the_error(
        self, client: AsyncClient, email_sender
    ):
        """The reverse direction -- a set that was fully consistent, then a
        later retake makes it inconsistent, must be caught too, not just
        the "was already broken" case above."""
        headers = await _auth_headers(client, email_sender, "photo-identity-regress@example.com")
        for angle in REQUIRED_ANGLES:
            resp = await _upload(client, headers, angle.id, _FIXTURE_FOR_ANGLE[angle.id])
            assert resp.status_code == 200, resp.text

        resp = await client.get("/photos/status", headers=headers)
        assert resp.json()["identity_check"]["consistent"] is True

        # different_person.jpg only passes its own per-photo checks (incl.
        # pose_match) for the "front" angle -- see the module-level fixture
        # comment above and TestCheckPhotoSetIdentity's front-mismatch test.
        resp = await _upload(client, headers, "front", "different_person.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"

        resp = await client.get("/photos/status", headers=headers)
        identity_check = resp.json()["identity_check"]
        assert identity_check["consistent"] is False
        assert identity_check["mismatched_angles"] == ["front"]

    async def test_replace_after_set_complete_is_allowed_before_payment(
        self, client: AsyncClient, email_sender
    ):
        """Review-screen Change flow: replace an angle after all three pass,
        as long as the user has not paid yet."""
        headers = await _auth_headers(client, email_sender, "photo-replace@example.com")
        for angle in REQUIRED_ANGLES:
            resp = await _upload(client, headers, angle.id, _FIXTURE_FOR_ANGLE[angle.id])
            assert resp.status_code == 200, resp.text

        resp = await _upload(client, headers, "front", "pass_all.jpg")
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"

    async def test_upload_after_payment_is_conflict(self, client: AsyncClient, email_sender, db):
        headers = await _auth_headers(client, email_sender, "photo-locked@example.com")
        for angle in REQUIRED_ANGLES:
            resp = await _upload(client, headers, angle.id, _FIXTURE_FOR_ANGLE[angle.id])
            assert resp.status_code == 200, resp.text

        me = await client.get("/auth/me", headers=headers)
        user_id = uuid.UUID(me.json()["id"])
        from app.models.payment import Payment

        db.add(
            Payment(
                user_id=user_id,
                stripe_session_id="cs_test_lock_photos",
                amount_cents=1999,
                currency="usd",
                status="succeeded",
            )
        )
        await db.commit()

        resp = await _upload(client, headers, "front", "pass_all.jpg")
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PHOTO_SET_ALREADY_COMPLETE"


class TestGetPhoto:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get(f"/photos/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_returns_own_photo(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-get@example.com")
        uploaded = await _upload(client, headers, "front", "pass_all.jpg")
        photo_id = uploaded.json()["id"]

        resp = await client.get(f"/photos/{photo_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == photo_id

    async def test_unknown_id_is_generic_404(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-404@example.com")
        resp = await client.get(f"/photos/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PHOTO_NOT_FOUND"

    async def test_other_users_photo_is_generic_404(self, client: AsyncClient, email_sender):
        headers_a = await _auth_headers(client, email_sender, "photo-owner-a@example.com")
        uploaded = await _upload(client, headers_a, "front", "pass_all.jpg")
        photo_id = uploaded.json()["id"]

        headers_b = await _auth_headers(client, email_sender, "photo-owner-b@example.com")
        resp = await client.get(f"/photos/{photo_id}", headers=headers_b)
        assert resp.status_code == 404


class TestGetPhotoFile:
    """The actual stored bytes -- lets the frontend show a persistent
    preview after a reload instead of only an ephemeral blob: URL."""

    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get(f"/photos/{uuid.uuid4()}/file")
        assert resp.status_code == 401

    async def test_returns_the_exact_uploaded_bytes(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-file@example.com")
        uploaded = await _upload(client, headers, "front", "pass_all.jpg")
        photo_id = uploaded.json()["id"]

        resp = await client.get(f"/photos/{photo_id}/file", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert resp.content == _load("pass_all.jpg")

    async def test_unknown_id_is_generic_404(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-file-404@example.com")
        resp = await client.get(f"/photos/{uuid.uuid4()}/file", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PHOTO_NOT_FOUND"

    async def test_other_users_photo_file_is_generic_404(self, client: AsyncClient, email_sender):
        headers_a = await _auth_headers(client, email_sender, "photo-file-owner-a@example.com")
        uploaded = await _upload(client, headers_a, "front", "pass_all.jpg")
        photo_id = uploaded.json()["id"]

        headers_b = await _auth_headers(client, email_sender, "photo-file-owner-b@example.com")
        resp = await client.get(f"/photos/{photo_id}/file", headers=headers_b)
        assert resp.status_code == 404

    async def test_retry_replaces_the_served_bytes(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-file-retry@example.com")
        first = await _upload(client, headers, "front", "too_small.jpg")
        photo_id = first.json()["id"]

        second = await _upload(client, headers, "front", "pass_all.jpg")
        assert second.json()["id"] == photo_id

        resp = await client.get(f"/photos/{photo_id}/file", headers=headers)
        assert resp.content == _load("pass_all.jpg")
