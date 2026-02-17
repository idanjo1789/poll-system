from datetime import datetime
from typing import List, Optional

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
    id: int = Field(..., alias="question_id")
    title: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        allow_population_by_field_name = True


class QuestionListResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    limit: int
    offset: int

