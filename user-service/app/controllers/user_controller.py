# app/controllers/user_controller.py
from typing import List

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from app.schemas.user_schemas import (
    CreateUserRequest,
    RegisterResponse,
    UpdateUserRequest,
    UserResponse,
    UserStatusResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(payload: CreateUserRequest) -> UserResponse:
    user = await UserService.create_user(payload)
    return UserResponse(**user)


@router.get(
    "",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[UserResponse]:
    users = await UserService.list_users(limit=limit, offset=offset)
    return [UserResponse(**u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user(user_id: int) -> UserResponse:
    user = await UserService.get_user(user_id)
    return UserResponse(**user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user(user_id: int, payload: UpdateUserRequest) -> UserResponse:
    user = await UserService.update_user(user_id, payload)
    return UserResponse(**user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_user(user_id: int) -> JSONResponse:
    """
    Deletes a user.
    Business rule: when a user is deleted, all of his poll answers must be deleted as well
    (via Poll Service internal API).
    """
    result = await UserService.delete_user(user_id)
    return JSONResponse(content=result, status_code=status.HTTP_200_OK)


@router.post(
    "/{user_id}/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_200_OK,
)
async def register_user(user_id: int) -> RegisterResponse:
    user = await UserService.register_user(user_id)
    return RegisterResponse(
        user_id=int(user["id"]),
        is_registered=bool(user["is_registered"]),
        message="User registered successfully",
    )


@router.get(
    "/{user_id}/status",
    response_model=UserStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def user_status(user_id: int) -> UserStatusResponse:
    data = await UserService.get_user_status(user_id)
    return UserStatusResponse(**data)
