"""Photo file storage, behind a swappable interface.

The storage mechanism was left open by the client (ASM-002,
docs/database-design.md §2.5's [Open Question]) -- resolved the same
pragmatic, non-blocking way the OTP-email-vendor question was (see
email_service.py's EmailSender/ConsoleEmailSender/get_email_sender()).
Picking a real object-storage vendor later is a new PhotoStorage
implementation, not a rewrite of photo_service.py.
"""

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

_BASE_DIR = Path(__file__).resolve().parent.parent.parent


class PhotoStorage(ABC):
    @abstractmethod
    async def save(self, *, user_id: uuid.UUID, angle: str, content: bytes, extension: str) -> str:
        """Persists the photo, returning an opaque storage_reference that
        `load`/`delete` can later use to find it again. Overwrites any
        existing file at the same (user_id, angle) -- callers upsert by
        angle, see photo_service.upload_photo."""

    @abstractmethod
    async def delete(self, storage_reference: str) -> None:
        """Best-effort; must not raise if the reference no longer exists."""


class LocalDiskPhotoStorage(PhotoStorage):
    """Dev/default: writes under PHOTO_STORAGE_LOCAL_DIR (gitignored --
    user-uploaded content, never committed). One file per (user_id, angle),
    named so a retry overwrites in lockstep with the upserted Photo row."""

    def __init__(self) -> None:
        settings = get_settings()
        self._root = _BASE_DIR / settings.photo_storage_local_dir

    async def save(self, *, user_id: uuid.UUID, angle: str, content: bytes, extension: str) -> str:
        user_dir = self._root / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        path = user_dir / f"{angle}{extension}"
        path.write_bytes(content)
        return str(path.relative_to(self._root))

    async def delete(self, storage_reference: str) -> None:
        path = self._root / storage_reference
        path.unlink(missing_ok=True)


class S3PhotoStorage(PhotoStorage):
    """Stub for a real deployment. boto3 is imported lazily so a
    local-provider deployment never needs it installed. S3_ENDPOINT_URL
    lets this target any S3-compatible provider (R2, MinIO, Spaces), not
    just AWS."""

    def __init__(self) -> None:
        import boto3  # noqa: PLC0415 -- lazy import, see class docstring

        settings = get_settings()
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            endpoint_url=settings.s3_endpoint_url,
        )

    async def save(self, *, user_id: uuid.UUID, angle: str, content: bytes, extension: str) -> str:
        key = f"{user_id}/{angle}{extension}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        return key

    async def delete(self, storage_reference: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=storage_reference)


@lru_cache
def get_photo_storage() -> PhotoStorage:
    settings = get_settings()
    if settings.photo_storage_provider == "local":
        return LocalDiskPhotoStorage()
    if settings.photo_storage_provider == "s3":
        return S3PhotoStorage()
    raise ValueError(f"Unsupported PHOTO_STORAGE_PROVIDER: {settings.photo_storage_provider!r}")
