import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MeasurementOut(BaseModel):
    available: bool
    metrics: dict[str, float] | None
    note: str | None


class FeatureScoreOut(BaseModel):
    """Milestone 2 (FR-018) -- one 0-100 score + label per report feature,
    from facial_assessment_service.compute_feature_scores. Backs the
    Dashboard's Overall Score / Priority Features to Improve list and 2 of
    the Harmony chart's 6 axes."""

    available: bool
    score: float | None = None
    label: str | None = None
    note: str | None = None
    # Short (1-2 word) dimension the score measures, e.g. "Width",
    # "Projection" -- lets the Dashboard say what to improve, not just
    # that a feature needs attention. None for pre-this-change reports.
    driver: str | None = None
    # report_design_spec.md v3.0 §13.1/§13.2 -- a short plain-language
    # phrase for `driver` (e.g. "Wider than typical"), shared by the
    # Priority Features sub-rows and the Feature Evaluation table's
    # "Finding" column. None where no directional/magnitude read applies.
    finding: str | None = None
    # report_template.md §3.8 -- a formatted typical/benchmark value for
    # `driver`, e.g. "~60% of face width". None where no single reference
    # value exists (never fabricated) -- renders as an empty cell.
    reference_value: str | None = None


class RecommendationItemOut(BaseModel):
    """FR-025/FR-024 (Milestone 3) -- one protocol/recommendation line
    item, carrying optional structured metadata alongside its text. Every
    field but `text` is nullable: report_assembly_service.normalize_recommendation_item
    never fabricates a value the AI didn't confidently supply -- a missing
    field renders as an omitted badge on the frontend, never a fake
    placeholder value."""

    text: str
    cost: str | None = None
    cadence: str | None = None
    time_to_effect: str | None = None
    difficulty: str | None = None
    # FR-024 -- paired with the feature's existing before/after image
    # (BeforeAfterBlock.tsx) for the first recommendation per feature only;
    # every item still carries these tags regardless of illustration.
    category: str | None = None
    risk_level: str | None = None
    product_or_method: str | None = None


class FeatureSectionOut(BaseModel):
    # Named narrative sub-sections (e.g. hair's "Hair Style"/"Hair Loss"/
    # "Hair Health") -- see ai_narrative_service.py's _FEATURE_SUBSECTIONS.
    # Replaces a single `narrative: str` field (2026-09-17, matching the
    # client reference report's own multi-sub-section depth per feature).
    # Empty for a pre-this-change report or when nothing was confidently
    # written -- never fabricated.
    sections: dict[str, str] = {}
    summary_callout: str
    strengths: str
    areas_of_note: str
    projected_potential: list[RecommendationItemOut]
    # AI-classified named attributes for this feature (e.g. hair's
    # hairline/texture/density), matching the depth of the client's own
    # reference report -- see ai_narrative_service.py's
    # _FEATURE_ATTRIBUTE_KEYS. Empty for a pre-this-change report or when
    # nothing was confidently assessable -- never fabricated.
    attributes: dict[str, str] = {}
    measurement: MeasurementOut
    # Whether GET /reports/{id}/features/{feature}/image has a cropped
    # image for this feature -- lets clients skip a request that would
    # just 404 (Hair/Neck/Ears crops are best-effort, see
    # facial_measurement_service.extract_feature_crops).
    has_image: bool
    # Milestone 2 (FR-022): "not_attempted" | "pending" | "generating" |
    # "generated" | "failed" -- a string enum, not a bool like has_image,
    # since the client needs to distinguish "still generating" from
    # "generation failed" from "this report predates FR-022 entirely"
    # (not_attempted). See report_service.py's visual-status projection.
    visual_status: str


class AssessmentDriverOut(BaseModel):
    """Milestone 2 (FR-018) -- one named contributor to an assessment, e.g.
    one of Dimorphism's top-3 drivers or one of Symmetry's Regional
    Balance entries."""

    feature: str
    score: float
    label: str
    citation: str


class FacialAssessmentOut(BaseModel):
    """Milestone 2 (FR-018) -- one of the 5 Facial Assessments (Dimorphism/
    Prototypicality/Proportions/Symmetry/Face Shape). Mirrors
    facial_assessment_service.AssessmentResult.to_dict()'s shape exactly.
    Every field defaults to None -- defensive: report_assembly_service.py
    should always send the full shape, but an unavailable entry built from
    a partial dict (rather than AssessmentResult.to_dict()) must not 500
    the whole report response over a few missing-but-meaningless keys."""

    available: bool
    score: float | None = None
    label: str | None = None
    slider_position: float | None = None
    drivers: list[AssessmentDriverOut] | None = None
    sub_scores: dict[str, AssessmentDriverOut] | None = None
    overlay: dict[str, Any] | None = None
    note: str | None = None


class FacialAgeOut(BaseModel):
    """report_design_spec.md v3.0 §15 -- a single current-estimate read
    (never a projection), AI-estimated from the photos alongside the rest
    of the narrative (ai_narrative_service.py). Absent entirely (not a
    zeroed/default instance) whenever the model couldn't confidently
    estimate -- see report_assembly_service.assemble_sections."""

    estimate: int
    note: str | None = None


class HairLossOut(BaseModel):
    """report_design_spec.md v3.0 §13.3 -- maps to the Hair page's
    illustrated 7-stage strip (Normal -> Need Attention -> Extreme).
    AI-estimated alongside the rest of the narrative; absent entirely
    (not a default stage) whenever not assessable from the photos."""

    stage: int
    label: str


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
    recommendations: dict[str, list[RecommendationItemOut]]
    closing_recommendations: str
    # Milestone 2 (FR-018) -- always all 5 keys (dimorphism/prototypicality/
    # proportions/symmetry/face_shape), all-unavailable for a pre-Milestone-2
    # report (see report_assembly_service.assemble_sections).
    facial_assessments: dict[str, FacialAssessmentOut]
    # Milestone 2 -- always all 11 ANALYSIS_FEATURES keys.
    feature_scores: dict[str, FeatureScoreOut]
    overall_score: float | None
    # Milestone 2 -- fixed 6 keys: harmony/symmetry/smoothness/jawline/skin/volume.
    harmony_chart: dict[str, float | None]
    # Dashboard consolidation -- real elapsed pipeline time (FacialAnalysisResult.
    # completed_at - created_at), for the Dashboard's "Analysis Time" stat.
    # None whenever completed_at is null (narrative still pending/failed) --
    # never fabricated, see app/api/routers/reports.py's _to_report_out.
    analysis_duration_seconds: float | None
    # report_design_spec.md v3.0 §15 / §13.3 -- both None whenever the AI
    # narrative call couldn't confidently estimate them, or for any report
    # generated before this change (never fabricated/defaulted).
    facial_age: FacialAgeOut | None = None
    hair_loss: HairLossOut | None = None


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
