from fastapi import APIRouter, Header, HTTPException, status

from config.config import settings
from repository import vote_repository


router = APIRouter(prefix="/internal", tags=["internal"])


def _require_internal_key(x_internal_key: str | None) -> None:
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


@router.delete("/users/{user_id}/votes")
async def delete_user_votes(
    user_id: int,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
):
    _require_internal_key(x_internal_key)

    await vote_repository.delete_votes_by_user_id(user_id)

    return {
        "status": "ok",
        "user_id": int(user_id),
    }
