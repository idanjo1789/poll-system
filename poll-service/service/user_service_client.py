from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class UserServiceClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Calls user-service: GET /users/{user_id}
        Returns:
            dict (user json) if exists
            None if 404
        Raises:
            httpx.HTTPError for network issues
            httpx.HTTPStatusError for non-2xx (except 404)
        """
        url = f"{self.base_url}/users/{user_id}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(url)

        if resp.status_code == 404:
            return None

        resp.raise_for_status()
        return resp.json()

    async def user_exists(self, user_id: int) -> bool:
        return (await self.get_user(user_id)) is not None
