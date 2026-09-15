"""AI Beauty Assistant chat endpoints (FR-019, Milestone 2 Phase 12) --
thin: all logic lives in app/services/chat_service.py. See
D:\\zzz\\chat-assistant\\plans.md.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ChatHistoryOut, MessageOut, SendMessageIn
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/history", response_model=ChatHistoryOut)
async def get_chat_history(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ChatHistoryOut:
    messages, suggested_prompts = await chat_service.get_history(db, user.id)
    return ChatHistoryOut(
        messages=[
            MessageOut(id=message.id, role=message.role, content=message.content, created_at=message.created_at)
            for message in messages
        ],
        suggested_prompts=suggested_prompts,
    )


@router.post("/messages")
async def send_chat_message(
    body: SendMessageIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Streams the assistant's reply as plain text chunks as they're
    generated -- not JSON, so this endpoint isn't `response_model`-typed
    like the rest of this project's endpoints. A medical/medication
    question short-circuits to a fixed refusal with zero AI provider
    calls (chat_service.stream_reply).

    prepare_reply is awaited here, BEFORE constructing StreamingResponse,
    so its AnalysisNotCompletedError (409) can still propagate to the
    normal exception handler -- an async generator's body doesn't start
    executing until Starlette begins sending the response, by which point
    the status code is already committed to 200. See chat_service.
    prepare_reply's docstring for the full explanation."""
    prepared = await chat_service.prepare_reply(db, user.id, body.content)
    return StreamingResponse(chat_service.stream_reply(db, prepared), media_type="text/plain")
