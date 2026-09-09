"""Photo file storage, behind a swappable interface.

The storage mechanism was left open by the client (ASM-002,
docs/database-design.md §2.5's [Open Question]) -- resolved the same
pragmatic, non-blocking way the OTP-email-vendor question was (see
email_service.py's EmailSender/ConsoleEmailSender/get_email_sender()).
Picking a real object-storage vendor later is a new PhotoStorage
implementation, not a rewrite of photo_service.py.

Default is DatabasePhotoStorage (PHOTO_STORAGE_PROVIDER=database) -- a
photo's bytes live in Postgres (PhotoBlob), not on the local filesystem.
This was changed from the original local-disk default so nothing is ever
written to var/photo_storage/ (a real problem on read-only/ephemeral
container filesystems, and it also unblocks GET /photos/{id}/file
serving a photo's actual bytes back to the frontend for a persistent
preview across a reload -- see photos.py). LocalDiskPhotoStorage and
S3PhotoStorage remain available and swappable via config, just no longer
the default.
"""

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.photo_blob import PhotoBlob

_BASE_DIR = Path(__file__).resolve().parent.parent.parent

_CONTENT_TYPE_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".heic": "image/heic",
}


class PhotoStorage(ABC):
    @abstractmethod
    async def save(self, *, user_id: uuid.UUID, angle: str, content: bytes, extension: str) -> str:
        """Persists the photo, returning an opaque storage_reference that
        `load`/`delete` can later use to find it again. Overwrites any
        existing file at the same (user_id, angle) -- callers upsert by
        angle, see photo_service.upload_photo."""

    @abstractmethod
    async def load(self, storage_reference: str) -> bytes:
        """Reads the photo back -- used by facial-analysis-engine (Phase 4)
        to feed the CV/AI pipeline with the actual stored bytes."""

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

    async def load(self, storage_reference: str) -> bytes:
        path = self._root / storage_reference
        return path.read_bytes()

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

    async def load(self, storage_reference: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=storage_reference)
        return response["Body"].read()  # type: ignore[no-any-return]

    async def delete(self, storage_reference: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=storage_reference)


class DatabasePhotoStorage(PhotoStorage):
    """The default. Stores photo bytes directly in Postgres (PhotoBlob)
    instead of the local filesystem or an object-storage bucket -- see
    this module's docstring for why.

    Manages its own short-lived DB session per call (the same pattern
    analysis_service.py's background task already uses) rather than
    threading a session through the PhotoStorage interface -- keeps this
    ABC's method signatures identical across all three implementations,
    at the cost of the blob write not sharing a transaction with the
    caller's Photo-row write. In practice a failure between the two just
    leaves either an orphaned blob (harmless, overwritten on retry) or a
    Photo row whose file 404s (caught explicitly, not a crash) -- an
    acceptable tradeoff for how rarely this can actually happen versus
    the alternative of changing the interface for every implementation.
    """

    async def save(self, *, user_id: uuid.UUID, angle: str, content: bytes, extension: str) -> str:
        reference = f"{user_id}/{angle}{extension}"
        content_type = _CONTENT_TYPE_BY_EXTENSION.get(extension, "application/octet-stream")
        async with async_session_factory() as db:
            blob = await db.get(PhotoBlob, reference)
            if blob is not None:
                blob.content = content
                blob.content_type = content_type
            else:
                db.add(PhotoBlob(id=reference, content=content, content_type=content_type))
            await db.commit()
        return reference

    async def load(self, storage_reference: str) -> bytes:
        async with async_session_factory() as db:
            blob = await db.get(PhotoBlob, storage_reference)
            if blob is None:
                raise FileNotFoundError(storage_reference)
            return blob.content

    async def delete(self, storage_reference: str) -> None:
        async with async_session_factory() as db:
            blob = await db.get(PhotoBlob, storage_reference)
            if blob is not None:
                await db.delete(blob)
                await db.commit()


def content_type_for(storage_reference: str) -> str:
    """The content-type a stored photo should be served back with --
    derived from the extension baked into its storage_reference (every
    PhotoStorage implementation names references the same way,
    "<user_id>/<angle><extension>"). Used by GET /photos/{id}/file."""
    extension = Path(storage_reference).suffix
    return _CONTENT_TYPE_BY_EXTENSION.get(extension, "application/octet-stream")


@lru_cache
def get_photo_storage() -> PhotoStorage:
    settings = get_settings()
    if settings.photo_storage_provider == "database":
        return DatabasePhotoStorage()
    if settings.photo_storage_provider == "local":
        return LocalDiskPhotoStorage()
    if settings.photo_storage_provider == "s3":
        return S3PhotoStorage()
    raise ValueError(f"Unsupported PHOTO_STORAGE_PROVIDER: {settings.photo_storage_provider!r}")
