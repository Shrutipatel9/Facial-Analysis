import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.photo import Photo
from app.services.photo_service import is_photo_set_ready
from app.services.photo_validation_service import REQUIRED_ANGLES
from tests.integration.test_auth_flow import _register_and_verify

pytestmark = pytest.mark.asyncio

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "photos"


def _load(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


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
            resp = await _upload(client, headers, angle.id, "pass_all.jpg")
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

        await _upload(client, headers, "left_3q", "pass_all.jpg")
        await _upload(client, headers, "right_3q", "pass_all.jpg")
        assert await is_photo_set_ready(db, user_id) is True

    async def test_upload_after_set_complete_is_conflict(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "photo-complete@example.com")
        for angle in REQUIRED_ANGLES:
            resp = await _upload(client, headers, angle.id, "pass_all.jpg")
            assert resp.status_code == 200, resp.text

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
