import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ChatHistoryOut(BaseModel):
    messages: list[MessageOut]
    # Always computed fresh from the report's current sections -- the
    # frontend shows these only when `messages` is empty.
    suggested_prompts: list[str]


class SendMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
