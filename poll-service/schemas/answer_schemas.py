from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class AnswerCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=255)


class AnswerResponse(BaseModel):
    answer_id: int
    question_id: int
    text: str
    choice: int = Field(..., ge=1, le=4) 
    created_at: datetime


class AnswerListResponse(BaseModel):
    items: List[AnswerResponse]
    total: int
    limit: int
    offset: int


