from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class VoteCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    choice: int = Field(..., ge=1, le=4)


class VoteUpdate(BaseModel):
    user_id: int = Field(..., ge=1)
    choice: int = Field(..., ge=1, le=4)


class VoteResponse(BaseModel):
    vote_id: int
    question_id: int
    user_id: int
    choice: int = Field(..., ge=1, le=4)
    created_at: datetime


class ChoiceResult(BaseModel):
    choice: int = Field(..., ge=1, le=4)
    votes: int


class QuestionResultsResponse(BaseModel):
    question_id: int
    total_votes: int
    results: List[ChoiceResult]
