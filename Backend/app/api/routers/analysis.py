"""Facial analysis endpoints -- thin: all logic lives in
app/services/analysis_service.py. See docs/api-specification.md §6.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analysis import AnalysisOut, AnalysisStatusResponse, TriggerAnalysisResponse
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("", response_model=TriggerAnalysisResponse)
async def trigger_analysis(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> TriggerAnalysisResponse:
    record = await analysis_service.trigger_analysis(db, user.id)
    return TriggerAnalysisResponse(id=record.id, status="processing")


@router.get("/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AnalysisStatusResponse:
    status_dict = await analysis_service.get_status(db, user.id)
    return AnalysisStatusResponse.model_validate(status_dict)


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisOut:
    record = await analysis_service.get_analysis(db, user.id, analysis_id)
    return AnalysisOut.model_validate(record)
