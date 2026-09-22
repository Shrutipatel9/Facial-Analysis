"""Crash-recovery reconciler (Milestone 3.1, Phase 21 -- production
hardening) -- resumes or fails out background work orphaned by a process
restart mid-generation.

No task queue exists anywhere in this stack (see
app/core/background_tasks.py's module docstring) -- durability instead
comes from a DB-backed "stuck past a threshold" sweep, reusing each
table's existing status/updated_at columns rather than new infrastructure.
This is a deliberate choice for a single-instance app with a durability
problem, not a throughput problem: a real queue (Celery/RQ/arq + Redis)
would mean new infra, a new worker process, and a new deployment topology
to fix "a coroutine died mid-flight." Revisit only if this app ever needs
multi-instance horizontal scaling -- this reconciler is not built to be
multi-worker-safe (no leader-election/locking), matching the app's current
single-Uvicorn-process deployment (see Backend/Dockerfile).

Three tables, three independent sweeps:
- FacialAnalysisResult ("processing" covers both the free CV step and the
  paid narrative step) -- see analysis_service.resume_analysis_pipeline.
- AiVisual ("generating" only -- "pending" orphans are already handled
  lazily by ai_visual_service.get_or_create_visuals on the user's next
  page visit, so this sweep only needs to catch the case that lazy check
  doesn't: a row stuck mid-generation with no page visit to trigger it).
- ReportFeatureVisual ("pending" or "generating" -- report_service has no
  lazy self-healing at all today, so this sweep is this table's *only*
  recovery path).

Run once at FastAPI startup (catches the previous process's death) and on
a periodic in-process sweep (app/main.py's lifespan).
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.background_tasks import schedule_background_task
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.ai_visual import AiVisual
from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.report_feature_visual import ReportFeatureVisual
from app.services import ai_visual_service, analysis_service, report_visual_service

logger = logging.getLogger(__name__)


def _cutoff() -> datetime:
    return datetime.now(UTC) - timedelta(minutes=get_settings().reconciler_stuck_threshold_minutes)


async def reconcile_analyses(db: AsyncSession) -> int:
    """Resumes FacialAnalysisResult rows stuck at "processing" past the
    threshold. Claims each row (touches updated_at) before dispatching its
    background resume -- resuming a real narrative call can itself take
    several minutes (up to ai_request_timeout_seconds), so without an
    immediate claim the *next* sweep (well within the stuck threshold)
    would see the same still-stale timestamp and schedule a second,
    duplicate resume for the same analysis."""
    settings = get_settings()
    result = await db.execute(
        select(FacialAnalysisResult)
        .where(FacialAnalysisResult.status == "processing", FacialAnalysisResult.updated_at < _cutoff())
        .limit(settings.reconciler_max_resumed_per_sweep)
    )
    rows = list(result.scalars().all())
    for record in rows:
        record.updated_at = datetime.now(UTC)
    if rows:
        await db.commit()
    for record in rows:
        logger.warning("Reconciler: resuming stuck analysis %s", record.id)
        schedule_background_task(analysis_service.resume_analysis_pipeline(record.id))
    return len(rows)


async def reconcile_ai_visuals(db: AsyncSession) -> int:
    """Resumes AiVisual (user_id, kind) sets with a row stuck "generating"
    past the threshold. reset_stuck_generating touches updated_at as a
    side effect of the status change, which is what keeps a subsequent
    sweep from re-selecting the same (now "pending") row."""
    settings = get_settings()
    result = await db.execute(
        select(AiVisual.user_id, AiVisual.kind)
        .where(AiVisual.status == "generating", AiVisual.updated_at < _cutoff())
        .distinct()
        .limit(settings.reconciler_max_resumed_per_sweep)
    )
    pairs = result.all()
    for user_id, kind in pairs:
        logger.warning("Reconciler: resuming stuck AI visuals %s/%s", user_id, kind)
        await ai_visual_service.reset_stuck_generating(db, user_id, kind)
        schedule_background_task(ai_visual_service.generate_all_visuals(user_id, kind))
    return len(pairs)


async def reconcile_report_visuals(db: AsyncSession) -> int:
    """Resumes reports with a ReportFeatureVisual row stuck "pending" or
    "generating" past the threshold. reset_stuck_rows touches updated_at
    as a side effect, same self-limiting reasoning as reconcile_ai_visuals."""
    settings = get_settings()
    result = await db.execute(
        select(ReportFeatureVisual.report_id)
        .where(
            ReportFeatureVisual.status.in_(("pending", "generating")),
            ReportFeatureVisual.updated_at < _cutoff(),
        )
        .distinct()
        .limit(settings.reconciler_max_resumed_per_sweep)
    )
    report_ids = [uuid.UUID(row) for row in result.scalars().all()]
    for report_id in report_ids:
        logger.warning("Reconciler: resuming stuck report visuals for report %s", report_id)
        await report_visual_service.reset_stuck_rows(db, report_id)
        schedule_background_task(report_visual_service.generate_all_feature_visuals(report_id))
    return len(report_ids)


async def run_reconciler_sweep() -> None:
    """One full pass across all three tables, its own DB session (same
    convention as every background task in this codebase). Called at
    FastAPI startup and on a periodic interval (app/main.py's lifespan)."""
    async with async_session_factory() as session:
        resumed_analyses = await reconcile_analyses(session)
        resumed_ai_visuals = await reconcile_ai_visuals(session)
        resumed_report_visuals = await reconcile_report_visuals(session)
    if resumed_analyses or resumed_ai_visuals or resumed_report_visuals:
        logger.warning(
            "Reconciler sweep resumed %d analyses, %d ai-visual kinds, %d report-visual reports",
            resumed_analyses,
            resumed_ai_visuals,
            resumed_report_visuals,
        )
