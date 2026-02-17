from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: bool = True


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None


class QuestionResponse(BaseModel):
    question_id: int
    title: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
