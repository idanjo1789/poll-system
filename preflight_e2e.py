"""
preflight_e2e.py
Run from host after docker compose up:
    python preflight_e2e.py

Env vars (optional):
    USER_SERVICE_BASE_URL=http://127.0.0.1:8001
    POLL_SERVICE_BASE_URL=http://127.0.0.1:8002
    INTERNAL_API_KEY=<your_internal_key>   # required only for internal delete votes test
"""

import os
import sys
import json
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx


USER_BASE = os.getenv("USER_SERVICE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
POLL_BASE = os.getenv("POLL_SERVICE_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
INTERNAL_KEY = os.getenv("INTERNAL_API_KEY", "").strip()

TIMEOUT = 10.0


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def warn(msg: str) -> None:
    print(f"⚠️  {msg}")


def fail(msg: str) -> None:
    print(f"❌ {msg}")
    raise RuntimeError(msg)


async def expect_status(resp: httpx.Response, expected: int, context: str) -> None:
    if resp.status_code != expected:
        body = resp.text
        # Keep output short but useful
        body_preview = body[:500] + ("..." if len(body) > 500 else "")
        fail(
            f"{context} expected HTTP {expected}, got {resp.status_code}. "
            f"Body preview: {body_preview}"
        )


async def get_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text}


@dataclass
class CreatedUser:
    user_id: int
    email: str


@dataclass
class CreatedQuestion:
    question_id: int


async def health_checks(client: httpx.AsyncClient) -> None:
    r1 = await client.get(f"{USER_BASE}/health")
    await expect_status(r1, 200, "user-service /health")
    ok("user-service /health OK")

    r2 = await client.get(f"{POLL_BASE}/health")
    await expect_status(r2, 200, "poll-service /health")
    ok("poll-service /health OK")


async def create_user(client: httpx.AsyncClient) -> CreatedUser:
    payload = {
        "first_name": "Idan",
        "last_name": "Test",
        "email": f"idan.preflight.{os.getpid()}@example.com",
        "age": 30,
        "address": "Haifa",
        "joining_date": "2024-01-01",
    }
    r = await client.post(f"{USER_BASE}/users", json=payload)
    await expect_status(r, 201, "POST /users create")
    data = await get_json(r)

    # Support both {"user_id":..} or {"id":..}
    user_id = data.get("user_id") or data.get("id")
    if not user_id:
        fail(f"POST /users response missing user_id/id. Got: {json.dumps(data, ensure_ascii=False)}")

    ok(f"Created user_id={user_id}")
    return CreatedUser(user_id=int(user_id), email=payload["email"])


async def register_user(client: httpx.AsyncClient, user_id: int) -> None:
    r = await client.patch(f"{USER_BASE}/users/{user_id}/register")
    # Some implementations use PUT/PATCH. If yours is PUT, change here.
    if r.status_code == 405:
        r = await client.put(f"{USER_BASE}/users/{user_id}/register")

    await expect_status(r, 200, f"register user {user_id}")
    ok(f"Registered user_id={user_id}")


async def create_question(client: httpx.AsyncClient) -> CreatedQuestion:
    payload = {
        "title": "Preflight Question",
        "description": "Choose 1..4",
        "is_active": True,
    }
    r = await client.post(f"{POLL_BASE}/questions", json=payload)
    await expect_status(r, 201, "POST /questions create")
    data = await get_json(r)

    qid = data.get("question_id") or data.get("id")
    if not qid:
        fail(f"POST /questions response missing question_id/id. Got: {json.dumps(data, ensure_ascii=False)}")

    ok(f"Created question_id={qid}")
    return CreatedQuestion(question_id=int(qid))


async def create_4_answers(client: httpx.AsyncClient, question_id: int) -> None:
    # Your API might be: POST /answers with {"question_id":..., "text":...}
    # or POST /questions/{id}/answers. We'll try common patterns.
    texts = ["A1", "A2", "A3", "A4"]
    created = 0

    for t in texts:
        payload = {"question_id": question_id, "text": t}
        r = await client.post(f"{POLL_BASE}/answers", json=payload)

        # fallback: /questions/{id}/answers
        if r.status_code in (404, 405):
            r = await client.post(f"{POLL_BASE}/questions/{question_id}/answers", json={"text": t})

        await expect_status(r, 201, f"create answer '{t}'")
        created += 1

    if created != 4:
        fail("Did not create 4 answers")
    ok("Created 4 answers for question")


async def vote_should_fail_for_unregistered_user(client: httpx.AsyncClient, user_id: int, question_id: int) -> None:
    payload = {"user_id": user_id, "question_id": question_id, "choice": 2}
    r = await client.post(f"{POLL_BASE}/votes", json=payload)

    # Accept either 403 or 409 or 400 depending on your design
    if r.status_code not in (400, 403, 409, 422):
        body = await get_json(r)
        fail(f"Expected unregistered vote to fail. Got {r.status_code}, body={body}")

    ok(f"Unregistered user vote blocked (HTTP {r.status_code})")


async def create_vote(client: httpx.AsyncClient, user_id: int, question_id: int, choice: int) -> int:
    payload = {"user_id": user_id, "question_id": question_id, "choice": choice}
    r = await client.post(f"{POLL_BASE}/votes", json=payload)
    await expect_status(r, 201, "POST /votes create")
    data = await get_json(r)

    vote_id = data.get("vote_id") or data.get("id")
    if not vote_id:
        # Some APIs return the vote row without id; handle gracefully
        warn(f"Vote created but missing vote_id in response: {data}")
        return -1

    ok(f"Created vote_id={vote_id} (choice={choice})")
    return int(vote_id)


async def duplicate_vote_should_fail(client: httpx.AsyncClient, user_id: int, question_id: int) -> None:
    payload = {"user_id": user_id, "question_id": question_id, "choice": 3}
    r = await client.post(f"{POLL_BASE}/votes", json=payload)

    if r.status_code not in (409, 400, 422):
        body = await get_json(r)
        fail(f"Expected duplicate vote to fail. Got {r.status_code}, body={body}")

    ok(f"Duplicate vote blocked (HTTP {r.status_code})")


async def update_vote(client: httpx.AsyncClient, user_id: int, question_id: int, new_choice: int) -> None:
    # Common patterns:
    # 1) PUT /votes with body {user_id,question_id,choice}
    # 2) PATCH /votes with same
    payload = {"user_id": user_id, "question_id": question_id, "choice": new_choice}

    r = await client.put(f"{POLL_BASE}/votes", json=payload)
    if r.status_code == 405:
        r = await client.patch(f"{POLL_BASE}/votes", json=payload)

    await expect_status(r, 200, "Update vote")
    ok(f"Updated vote to choice={new_choice}")


async def invalid_choice_should_fail(client: httpx.AsyncClient, user_id: int, question_id: int) -> None:
    payload = {"user_id": user_id, "question_id": question_id, "choice": 7}
    r = await client.post(f"{POLL_BASE}/votes", json=payload)
    if r.status_code not in (400, 422):
        body = await get_json(r)
        fail(f"Expected invalid choice to fail. Got {r.status_code}, body={body}")
    ok(f"Invalid choice blocked (HTTP {r.status_code})")


async def delete_user_and_verify_votes_deleted(client: httpx.AsyncClient, user_id: int) -> None:
    # Delete user in user-service
    r = await client.delete(f"{USER_BASE}/users/{user_id}")
    if r.status_code not in (200, 204):
        await expect_status(r, 200, "DELETE /users/{id}")
    ok(f"Deleted user_id={user_id} in user-service")

    # Now verify via internal endpoint on poll-service (if key provided).
    if not INTERNAL_KEY:
        warn("INTERNAL_API_KEY not set; skipping internal votes deletion verification.")
        return

    # Depending on your design, user-service calls poll-service itself.
    # Here we just try to ensure that after deletion, internal endpoint confirms no votes remain.
    r2 = await client.get(
        f"{POLL_BASE}/internal/users/{user_id}/votes",
        headers={"X-Internal-Key": INTERNAL_KEY},
    )

    # If you don't have GET internal, skip gracefully
    if r2.status_code == 404 or r2.status_code == 405:
        warn("No internal GET /internal/users/{id}/votes endpoint found; skipping verification.")
        return

    await expect_status(r2, 200, "Internal get votes by user")
    data = await get_json(r2)

    # Expect either {"count":0} or {"items":[]} etc.
    count = None
    if isinstance(data, dict):
        if "count" in data:
            count = int(data["count"])
        elif "items" in data and isinstance(data["items"], list):
            count = len(data["items"])

    if count is None:
        warn(f"Internal votes response format unknown. Got: {data}")
        return

    if count != 0:
        fail(f"Expected votes deleted for user {user_id}, but count={count}")

    ok("Votes deleted after user deletion (verified)")

    # Also optionally call DELETE internal to ensure idempotency
    r3 = await client.delete(
        f"{POLL_BASE}/internal/users/{user_id}/votes",
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    if r3.status_code not in (200, 204, 404):
        await expect_status(r3, 200, "Internal delete votes by user (idempotent)")
    ok("Internal delete votes endpoint idempotency OK")


async def main() -> None:
    print("=== Preflight E2E checks ===")
    print(f"USER_BASE = {USER_BASE}")
    print(f"POLL_BASE = {POLL_BASE}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        await health_checks(client)

        # Create user (unregistered)
        user = await create_user(client)

        # Create question + answers
        q = await create_question(client)
        await create_4_answers(client, q.question_id)

        # Unregistered user should fail
        await vote_should_fail_for_unregistered_user(client, user.user_id, q.question_id)

        # Register user and vote
        await register_user(client, user.user_id)
        await invalid_choice_should_fail(client, user.user_id, q.question_id)

        await create_vote(client, user.user_id, q.question_id, choice=2)
        await duplicate_vote_should_fail(client, user.user_id, q.question_id)

        # Update vote
        await update_vote(client, user.user_id, q.question_id, new_choice=4)

        # Delete user -> votes should be deleted
        await delete_user_and_verify_votes_deleted(client, user.user_id)

    ok("ALL PREFLIGHT CHECKS PASSED ✅")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        print("\nPreflight failed.")
        sys.exit(2)
