from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ReportFeatureImage(Base):
    """A cropped region of the user's front-angle photo for one report
    feature (e.g. "the eyes region"), used only for report imagery -- see
    facial_measurement_service.extract_feature_crops(). Not every feature
    has a usable crop (Hair/Neck/Ears are best-effort; a missing row means
    "no image available for this feature", not an error.

    One row per (report_id, feature) -- composite PK, mirrors PhotoBlob's
    decoupled-storage shape but keyed by two columns instead of one opaque
    reference string, since both are already known at read time
    (GET /reports/{id}/features/{feature}/image).
    """

    __tablename__ = "report_feature_images"

    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    feature: Mapped[str] = mapped_column(String(32), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/jpeg")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
