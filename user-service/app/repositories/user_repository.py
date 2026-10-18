from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db import database


class UserRepository:
    """
    DB access layer for users table (async).
    NOTE: With `databases`, on some setups it's safer to pass SQL as plain strings
    (not sqlalchemy.text()) to avoid TextClause .values() errors.
    """

    # --- CREATE ---
    @staticmethod
    async def create_user(data: Dict[str, Any]) -> int:
        joining_date = data.get("joining_date") or datetime.utcnow()

        query = """
            INSERT INTO users (first_name, last_name, email, age, address, joining_date, is_registered)
            VALUES (:first_name, :last_name, :email, :age, :address, :joining_date, 0)
        """

        new_id = await database.execute(
            query,
            {
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "email": data["email"],
                "age": data["age"],
                "address": data["address"],
                "joining_date": joining_date,
            },
        )
        return int(new_id)

    # --- READ ---
    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        row = await database.fetch_one(
            "SELECT * FROM users WHERE id = :user_id",
            {"user_id": user_id},
        )
        return dict(row) if row else None

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        row = await database.fetch_one(
            "SELECT * FROM users WHERE email = :email",
            {"email": email},
        )
        return dict(row) if row else None

    @staticmethod
    async def list_users(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        # Keep safe casting; also avoids driver issues with LIMIT bind params
        limit = int(limit)
        offset = int(offset)

        rows = await database.fetch_all(
            f"""
            SELECT * FROM users
            ORDER BY id
            LIMIT {limit} OFFSET {offset}
            """
        )
        return [dict(r) for r in rows]

    # --- UPDATE ---
    @staticmethod
    async def update_user(user_id: int, data: Dict[str, Any]) -> bool:
        allowed_fields = {"first_name", "last_name", "email", "age", "address"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

        exists = await database.fetch_one(
            "SELECT id FROM users WHERE id = :user_id",
            {"user_id": user_id},
        )
        if not exists:
            return False
        if not update_data:
            return True

        set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
        query = f"UPDATE users SET {set_clause} WHERE id = :user_id"

        params = {**update_data, "user_id": user_id}
        await database.execute(query, params)
        return True

    # --- DELETE ---
    @staticmethod
    async def delete_user(user_id: int) -> bool:
        exists = await database.fetch_one(
            "SELECT id FROM users WHERE id = :user_id",
            {"user_id": user_id},
        )
        if not exists:
            return False

        await database.execute(
            "DELETE FROM users WHERE id = :user_id",
            {"user_id": user_id},
        )
        return True

    # --- REGISTER / STATUS ---
    @staticmethod
    async def set_registered(user_id: int) -> bool:
        exists = await database.fetch_one(
            "SELECT id FROM users WHERE id = :user_id",
            {"user_id": user_id},
        )
        if not exists:
            return False

        await database.execute(
            "UPDATE users SET is_registered = 1 WHERE id = :user_id",
            {"user_id": user_id},
        )
        return True

    @staticmethod
    async def get_registration_status(user_id: int) -> Optional[bool]:
        row = await database.fetch_one(
            "SELECT is_registered FROM users WHERE id = :user_id",
            {"user_id": user_id},
        )
        if not row:
            return None
        return bool(row["is_registered"])
