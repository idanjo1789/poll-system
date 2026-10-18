# app/services/user_service.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app import config
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUserRequest, UpdateUserRequest


class UserService:
    """
    Business rules:
    - email must be unique
    - is_registered cannot be updated via update_user (only via register_user)
    - when deleting a user, must also delete all their votes in poll-service
    """

    @staticmethod
    def _poll_service_base_url() -> str:
        return config.POLL_SERVICE_BASE_URL.rstrip("/")

    @staticmethod
    def _internal_api_key() -> str:
        key = (config.INTERNAL_API_KEY or "").strip()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="INTERNAL_API_KEY not configured in user-service",
            )
        return key

    @staticmethod
    async def _delete_user_votes_in_poll_service(user_id: int) -> None:
        url = f"{UserService._poll_service_base_url()}/internal/users/{int(user_id)}/votes"
        headers = {"X-Internal-Key": UserService._internal_api_key()}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.delete(url, headers=headers)
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="poll-service is unavailable. Cannot delete user's votes.",
            )

        if 200 <= resp.status_code < 300:
            return

        if resp.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="poll-service rejected internal key (X-Internal-Key). Check INTERNAL_API_KEY on both services.",
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"poll-service error while deleting votes (status={resp.status_code})",
        )

    # ---------------- CRUD ----------------

    @staticmethod
    async def create_user(data: CreateUserRequest) -> Dict[str, Any]:
        existing = await UserRepository.get_user_by_email(data.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        fields = {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "email": data.email,
            "age": data.age,
            "address": data.address,
            "joining_date": datetime.utcnow(),
            "is_registered": 0,
        }

        user_id = await UserRepository.create_user(fields)
        user = await UserRepository.get_user_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
        return user

    @staticmethod
    async def get_user(user_id: int) -> Dict[str, Any]:
        user = await UserRepository.get_user_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    async def list_users(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return await UserRepository.list_users(limit=limit, offset=offset)

    @staticmethod
    async def update_user(user_id: int, data: UpdateUserRequest) -> Dict[str, Any]:
        user = await UserRepository.get_user_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        fields = data.dict(exclude_none=True)

        # Enforce immutability here (business rule)
        fields.pop("is_registered", None)
        fields.pop("id", None)
        fields.pop("joining_date", None)

        if not fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

        if "email" in fields:
            existing = await UserRepository.get_user_by_email(fields["email"])
            if existing and int(existing["id"]) != int(user_id):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        ok = await UserRepository.update_user(int(user_id), fields)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        updated = await UserRepository.get_user_by_id(int(user_id))
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated

    @staticmethod
    async def register_user(user_id: int) -> Dict[str, Any]:
        user = await UserRepository.get_user_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        ok = await UserRepository.set_registered(int(user_id))
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        updated = await UserRepository.get_user_by_id(int(user_id))
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated

    @staticmethod
    async def get_user_status(user_id: int) -> Dict[str, Any]:
        status_value: Optional[bool] = await UserRepository.get_registration_status(int(user_id))
        if status_value is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {"user_id": int(user_id), "is_registered": bool(status_value)}

    @staticmethod
    async def delete_user(user_id: int) -> Dict[str, Any]:
        user = await UserRepository.get_user_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await UserService._delete_user_votes_in_poll_service(int(user_id))

        ok = await UserRepository.delete_user(int(user_id))
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return {"message": "User deleted", "user_id": int(user_id)}
