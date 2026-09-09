from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class PhotoBlob(Base):
    """Raw photo bytes, used only by DatabasePhotoStorage
    (PHOTO_STORAGE_PROVIDER=database, the default) -- deliberately
    decoupled from the Photo model itself so the storage backend stays
    swappable without touching Photo's own schema, per photo_storage.py's
    module docstring.

    `id` is the opaque storage_reference string PhotoStorage.save()
    returns and PhotoStorage.load()/delete() are given back -- not a FK.
    One row per (user_id, angle), same upsert-in-place posture as the
    Photo row itself.
    """

    __tablename__ = "photo_blobs"

    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
