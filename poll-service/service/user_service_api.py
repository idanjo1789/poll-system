from typing import Any

import httpx

from config.config import settings


async def get_user(user_id: int) -> dict[str, Any] | None:
    """
    Calls user-service: GET /users/{user_id}

    Returns:
        dict if user exists
        None if 404

    Raises:
        httpx.HTTPError on network errors / non-2xx (except 404)
    """

    url = f"{settings.USER_SERVICE_BASE_URL}/users/{int(user_id)}"

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()
