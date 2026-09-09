import uuid
from datetime import datetime

from pydantic import BaseModel


class MeasurementOut(BaseModel):
    available: bool
    metrics: dict[str, float] | None
    note: str | None


class FeatureSectionOut(BaseModel):
    narrative: str
    summary_callout: str
    strengths: str
    areas_of_note: str
    projected_potential: list[str]
    measurement: MeasurementOut
    # Whether GET /reports/{id}/features/{feature}/image has a cropped
    # image for this feature -- lets clients skip a request that would
    # just 404 (Hair/Neck/Ears crops are best-effort, see
    # facial_measurement_service.extract_feature_crops).
    has_image: bool


class ReportTeaserOut(BaseModel):
    """Intro copy plus each feature's one-line summary callout -- kept as
    a distinct sub-shape (rather than folded into the full section) since
    it doubles as the report's own summary header, not because it is
    gated separately anymore. A Report can only exist once payment has
    already succeeded (analysis_service.trigger_analysis's own guard), so
    there is no pre-payment state to show it in."""

    intro: str
    feature_summaries: dict[str, str]


class ReportFullContentOut(BaseModel):
    understanding_your_results: str
    limitations: str
    features: dict[str, FeatureSectionOut]
    recommendations: dict[str, list[str]]
    closing_recommendations: str


class ReportOut(BaseModel):
    id: uuid.UUID
    publish_state: str
    created_at: datetime
    teaser: ReportTeaserOut
    full: ReportFullContentOut


class ReportSummaryOut(BaseModel):
    id: uuid.UUID
    publish_state: str
    created_at: datetime

    model_config = {"from_attributes": True}
