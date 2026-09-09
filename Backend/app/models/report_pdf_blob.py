from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ReportPdfBlob(Base):
    """Raw rendered PDF bytes for a Report, generated lazily on first
    GET /reports/{id}/pdf and cached here -- mirrors PhotoBlob's
    decoupled-storage shape (id is the opaque pdf_reference string, not a
    FK). No swappable-storage ABC here unlike PhotoStorage: there is no
    current requirement for an S3/local alternative for this artifact, so a
    single DB-backed table is used directly rather than building an
    interface layer with only one real implementation.
    """

    __tablename__ = "report_pdf_blobs"

    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
