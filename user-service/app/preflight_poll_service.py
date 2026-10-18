# preflight_poll_service.py
# Run:
#   python preflight_poll_service.py
#
# Env (optional):
#   set POLL_BASE_URL=http://127.0.0.1:8002
#   set USER_BASE_URL=http://127.0.0.1:8001
#   set INTERNAL_API_KEY=your_key   (only if you want to test internal endpoint directly)

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

POLL_BASE_URL = os.getenv("POLL_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
USER_BASE_URL = os.getenv("USER_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")  # optional


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def fail(msg: str) -> None:
    raise RuntimeError(f"❌ {msg}")


def uniq_email(prefix: str) -> str:
    return f"{prefix}.{int(time.time()*1000)}@example.com"


async def assert_status(resp: httpx.Response, expected: int, context: str) -> None:
    if resp.status_code != expected:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        fail(f"{context}: expected {expected}, got {resp.status_code}. Body: {body}")


async def create_user(client: httpx.AsyncClient, first="Idan", last="Test", registered: bool = False) -> Dict[str, Any]:
    payload = {
        "first_name": first,
        "last_name": last,
        "email": uniq_email("idan"),
        "age": 30,
        "address": "Tel Aviv",
        "joining_date": datetime.utcnow().date().isoformat(),
        # is_registered should probably be set by register endpoint; still include if your schema allows
        "is_registered": registered,
    }
    r = await client.post(f"{USER_BASE_URL}/users", json=payload)
    await assert_status(r, 201, "Create user")
    return r.json()


async def register_user(client: httpx.AsyncClient, user_id: int) -> None:
    r = await client.post(f"{USER_BASE_URL}/users/{user_id}/register")
    # depending on your user-service it might be POST/PUT; change if needed
    if r.status_code not in (200, 201):
        await assert_status(r, 200, "Register user")
    ok(f"User registered: {user_id}")


async def delete_user(client: httpx.AsyncClient, user_id: int) -> None:
    r = await client.delete(f"{USER_BASE_URL}/users/{user_id}")
    await assert_status(r, 200, "Delete user")
    ok(f"User deleted: {user_id}")


async def create_question(client: httpx.AsyncClient) -> Dict[str, Any]:
    payload = {"title": "Preflight Question", "description": "E2E test", "is_active": True}
    r = await client.post(f"{POLL_BASE_URL}/questions", json=payload)
    await assert_status(r, 201, "Create question")
    return r.json()


async def create_answer(client: httpx.AsyncClient, question_id: int, text: str) -> Dict[str, Any]:
    r = await client.post(f"{POLL_BASE_URL}/questions/{question_id}/answers", json={"text": text})
    await assert_status(r, 201, "Create answer")
    return r.json()


async def list_answers(client: httpx.AsyncClient, question_id: int) -> Dict[str, Any]:
    r = await client.get(f"{POLL_BASE_URL}/questions/{question_id}/answers", params={"limit": 10, "offset": 0})
    await assert_status(r, 200, "List answers")
    return r.json()


async def vote_create(client: httpx.AsyncClient, question_id: int, user_id: int, choice: int) -> Dict[str, Any]:
    r = await client.post(f"{POLL_BASE_URL}/questions/{question_id}/vote", json={"user_id": user_id, "choice": choice})
    await assert_status(r, 201, "Create vote")
    return r.json()


async def vote_update(client: httpx.AsyncClient, question_id: int, user_id: int, choice: int) -> Dict[str, Any]:
    r = await client.put(f"{POLL_BASE_URL}/questions/{question_id}/vote", json={"user_id": user_id, "choice": choice})
    await assert_status(r, 200, "Update vote")
    return r.json()


async def internal_delete_votes(client: httpx.AsyncClient, user_id: int) -> None:
    if not INTERNAL_API_KEY:
        ok("Skipped internal delete votes test (INTERNAL_API_KEY not set)")
        return
    r = await client.delete(
        f"{POLL_BASE_URL}/internal/users/{user_id}/votes",
        headers={"X-Internal-Key": INTERNAL_API_KEY},
    )
    await assert_status(r, 200, "Internal delete votes")
    ok(f"Internal votes delete OK for user {user_id}")


async def main() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Health checks
        r1 = await client.get(f"{POLL_BASE_URL}/health")
        await assert_status(r1, 200, "Poll health")
        ok("poll-service /health OK")

        r2 = await client.get(f"{USER_BASE_URL}/health")
        await assert_status(r2, 200, "User health")
        ok("user-service /health OK")

        # Create users
        u_registered = await create_user(client, first="Idan", last="Registered", registered=False)
        u_unregistered = await create_user(client, first="Idan", last="Unregistered", registered=False)

        registered_id = int(u_registered["user_id"])
        unregistered_id = int(u_unregistered["user_id"])

        # Register only one of them
        await register_user(client, registered_id)

        # Create question
        q = await create_question(client)
        question_id = int(q.get("question_id") or q.get("id") or q.get("questionId", 0))
        if not question_id:
            fail(f"Question id not found in response: {q}")
        ok(f"Question created: {question_id}")

        # Create 4 answers
        for i in range(1, 5):
            a = await create_answer(client, question_id, text=f"Answer {i}")
            ok(f"Answer {i} created (answer_id={a.get('answer_id')}, choice={a.get('choice')})")

        # 5th answer must fail with 409
        r = await client.post(f"{POLL_BASE_URL}/questions/{question_id}/answers", json={"text": "Answer 5"})
        if r.status_code != 409:
            fail(f"Expected 409 on 5th answer, got {r.status_code}. Body: {r.text}")
        ok("5th answer blocked (409) OK")

        # List answers and verify choices 1..4
        answers_list = await list_answers(client, question_id)
        items = answers_list.get("items", [])
        if len(items) != 4:
            fail(f"Expected 4 answers in list, got {len(items)}. Body: {answers_list}")

        choices = [int(x["choice"]) for x in items]
        if choices != [1, 2, 3, 4]:
            fail(f"Expected choices [1,2,3,4], got {choices}")
        ok("Answers list OK (choices 1..4)")

        # Vote create (registered)
        v = await vote_create(client, question_id, registered_id, choice=2)
        ok(f"Vote created: vote_id={v.get('vote_id')} choice={v.get('choice')}")

        # Duplicate vote must 409
        r = await client.post(f"{POLL_BASE_URL}/questions/{question_id}/vote", json={"user_id": registered_id, "choice": 3})
        if r.status_code != 409:
            fail(f"Expected 409 on duplicate vote, got {r.status_code}. Body: {r.text}")
        ok("Duplicate vote blocked (409) OK")

        # Update vote
        v2 = await vote_update(client, question_id, registered_id, choice=4)
        if int(v2.get("choice")) != 4:
            fail(f"Expected updated choice=4, got {v2}")
        ok("Vote update OK")

        # Unregistered user cannot vote -> 403
        r = await client.post(f"{POLL_BASE_URL}/questions/{question_id}/vote", json={"user_id": unregistered_id, "choice": 1})
        if r.status_code != 403:
            fail(f"Expected 403 for unregistered user vote, got {r.status_code}. Body: {r.text}")
        ok("Unregistered user blocked (403) OK")

        # Delete registered user (should trigger cascade deletion via internal call in your user-service)
        await delete_user(client, registered_id)

        # After deletion: voting again should be 404 (user not found) OR 403 (depends on your user-service get_user behavior)
        r = await client.post(f"{POLL_BASE_URL}/questions/{question_id}/vote", json={"user_id": registered_id, "choice": 1})
        if r.status_code not in (404, 403):
            fail(f"Expected 404/403 after user deletion, got {r.status_code}. Body: {r.text}")
        ok("Vote after user deletion blocked (404/403) OK")

        # Optional: directly test internal deletion endpoint (only if INTERNAL_API_KEY is set)
        await internal_delete_votes(client, unregistered_id)

        # Cleanup: delete second user
        await delete_user(client, unregistered_id)

        ok("ALL PREFLIGHT CHECKS PASSED ✅")


if __name__ == "__main__":
    asyncio.run(main())
