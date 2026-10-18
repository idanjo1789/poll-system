from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    age: int = Field(..., ge=0, le=120)
    address: str = Field(..., min_length=1, max_length=255)


class UpdateUserRequest(BaseModel):
    # All optional - partial update behavior
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    age: Optional[int] = Field(None, ge=0, le=120)
    address: Optional[str] = Field(None, min_length=1, max_length=255)
    is_registered: Optional[bool] = None 


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    age: int
    address: str
    joining_date: datetime
    is_registered: bool


class UserStatusResponse(BaseModel):
    user_id: int
    is_registered: bool


class RegisterResponse(BaseModel):
    user_id: int
    is_registered: bool
    message: str