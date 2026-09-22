"""AI visual-preview endpoints (FR-020, Milestone 2 Phase 11) -- thin: all
logic lives in app/services/ai_visual_service.py. See
D:\\zzz\\ai-visuals-hairstyle\\plans.md.
"""

import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.ai_visual import AiVisual
from app.models.user import User
from app.schemas.ai_visuals import AiVisualKind, AiVisualOut
from app.services import ai_visual_service

router = APIRouter(prefix="/ai-visuals", tags=["ai-visuals"])


def _to_out(row: AiVisual) -> AiVisualOut:
    return AiVisualOut(
        id=row.id,
        kind=row.kind,
        variation_index=row.variation_index,
        status=row.status,
        name=row.name,
        is_recommended=row.is_recommended,
        attributes=row.attributes,
        explanation=row.explanation,
        error_reason=row.error_reason,
    )


@router.post("/{kind}", response_model=list[AiVisualOut])
@limiter.limit("10/hour")
async def create_visuals(
    request: Request,
    kind: AiVisualKind,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AiVisualOut]:
    """Lazy get-or-create + trigger-once (BR-006) -- idempotent/safe to call
    repeatedly once rows exist, same posture as POST /reports. Rate limited
    per exact path (slowapi's default key includes the request path, so
    each `{kind}` value -- hairstyle/outfit/aging/potential -- gets its own
    independent 10/hour bucket, confirmed via
    tests/integration/test_rate_limiting.py), slightly more generous than a
    pure one-shot trigger (5/hour, see trigger_analysis) since a legitimate
    retry-after-transient-failure flow (get_or_create_visuals' own
    retryable-failure reset) reuses this same endpoint rather than a
    separate retry action."""
    rows = await ai_visual_service.get_or_create_visuals(db, user.id, kind)
    return [_to_out(row) for row in rows]


@router.get("/{kind}", response_model=list[AiVisualOut])
async def list_visuals(
    kind: AiVisualKind,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AiVisualOut]:
    """Read-only, never auto-triggers -- returns [] before the first POST."""
    rows = await ai_visual_service.get_visuals(db, user.id, kind)
    return [_to_out(row) for row in rows]


@router.get("/{kind}/{variation_id}/image")
async def get_visual_image(
    kind: AiVisualKind,
    variation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """200 image bytes only once generation has completed; 404 otherwise
    (pending/generating/failed/unknown all collapse to the same
    AiVisualNotFoundError, same anti-enumeration posture as the report
    feature-visual endpoint)."""
    content = await ai_visual_service.get_visual_image(db, user.id, kind, variation_id)
    return Response(content=content, media_type="image/png")
