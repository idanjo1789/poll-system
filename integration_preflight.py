# integration_preflight.py
# Run from project root (host):
#   python .\integration_preflight.py
#
# Optional env overrides:
#   USER_BASE_URL=http://127.0.0.1:8001
#   POLL_BASE_URL=http://127.0.0.1:8002
#   INTERNAL_API_KEY=super-secret-key

import asyncio
import os
import uuid
from typing import Any, Iterable, Optional, Tuple, Union

import httpx

USER_BASE_URL = os.getenv("USER_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
POLL_BASE_URL = os.getenv("POLL_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "super-secret-key")


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def warn(msg: str) -> None:
    print(f"⚠️  {msg}")


def fail(msg: str) -> None:
    raise RuntimeError(f"❌ {msg}")


ExpectedType = Union[int, Iterable[int]]


async def req(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    expected: ExpectedType,
    *,
    json: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> Any:
    exp: Tuple[int, ...] = (expected,) if isinstance(expected, int) else tuple(expected)
    r = await client.request(method, url, json=json, headers=headers)
    body_text = (r.text or "").strip()

    if r.status_code not in exp:
        fail(f"{method} {url} -> {r.status_code} (expected {exp}). Body: {body_text}")

    if "application/json" in (r.headers.get("content-type") or "") and body_text:
        return r.json()
    return body_text


def pick_id(obj: dict, *keys: str) -> int:
    for k in keys:
        v = obj.get(k)
        if v is not None:
            return int(v)
    fail(f"Response missing expected id field. Tried: {keys}. Got: {obj}")


async def pick_first_working_vote_path(
    client: httpx.AsyncClient, question_id: int, user_id_for_probe: int
) -> str:
    """
    Some projects use:
      POST /questions/{id}/vote, PUT /questions/{id}/vote
    Others might use:
      POST /questions/{id}/votes, PUT /questions/{id}/votes
    We'll probe and pick the first endpoint that is not 404/405.
    """
    candidates = [
        f"{POLL_BASE_URL}/questions/{question_id}/vote",
        f"{POLL_BASE_URL}/questions/{question_id}/votes",
    ]

    for url in candidates:
        r = await client.post(url, json={"user_id": user_id_for_probe, "choice": 1})
        if r.status_code in (404, 405):
            continue
        # Found a real endpoint (even if it returned 403/422/409/etc)
        return url

    fail(f"Could not find a working vote endpoint. Tried: {candidates}")
    return ""


async def main() -> None:
    print("=== Integration Preflight: user-service <-> poll-service (no answers table) ===")
    print(f"USER_BASE_URL = {USER_BASE_URL}")
    print(f"POLL_BASE_URL = {POLL_BASE_URL}")
    print(f"INTERNAL_API_KEY = {'***' if INTERNAL_API_KEY else '(empty)'}\n")

    unique = uuid.uuid4().hex[:8]

    async with httpx.AsyncClient(timeout=12.0) as client:
        # 0) Health checks
        await req(client, "GET", f"{USER_BASE_URL}/health", 200)
        ok("user-service /health OK")

        await req(client, "GET", f"{POLL_BASE_URL}/health", 200)
        ok("poll-service /health OK")

        # 1) Create unregistered + registered users
        u_unreg = await req(
            client,
            "POST",
            f"{USER_BASE_URL}/users",
            (200, 201),
            json={
                "first_name": "Test",
                "last_name": "Unreg",
                "email": f"unreg_{unique}@example.com",
                "age": 30,
                "address": "Somewhere",
            },
        )
        user_unreg_id = pick_id(u_unreg, "id", "user_id")
        ok(f"Created user (NOT registered) user_id={user_unreg_id}")

        u_reg = await req(
            client,
            "POST",
            f"{USER_BASE_URL}/users",
            (200, 201),
            json={
                "first_name": "Test",
                "last_name": "Reg",
                "email": f"reg_{unique}@example.com",
                "age": 31,
                "address": "Somewhere",
            },
        )
        user_reg_id = pick_id(u_reg, "id", "user_id")
        ok(f"Created user (to register) user_id={user_reg_id}")

        await req(client, "POST", f"{USER_BASE_URL}/users/{user_reg_id}/register", (200, 201))
        ok("User registered OK")

        # 2) Create question
        q = await req(
            client,
            "POST",
            f"{POLL_BASE_URL}/questions",
            (200, 201),
            json={"title": f"Question {unique}", "description": "Integration test", "is_active": True},
        )
        question_id = pick_id(q, "question_id", "id")
        ok(f"Created question question_id={question_id}")

        # 3) Discover vote endpoint style
        vote_url = await pick_first_working_vote_path(client, question_id, user_unreg_id)
        ok(f"Using vote endpoint: {vote_url}")

        # 4) Unregistered user cannot vote => expect 403
        r = await client.post(vote_url, json={"user_id": user_unreg_id, "choice": 2})
        if r.status_code != 403:
            fail(f"Expected 403 for unregistered user voting. Got {r.status_code}. Body: {(r.text or '').strip()}")
        ok("Unregistered user voting blocked with 403")

        # 5) Non-existent user => expect 404 (some implementations may return 403; warn if so)
        r = await client.post(vote_url, json={"user_id": 99999999, "choice": 2})
        if r.status_code == 404:
            ok("Non-existent user voting blocked with 404")
        elif r.status_code == 403:
            warn("Non-existent user voting returned 403 (acceptable if you don't distinguish 404 vs 403).")
        else:
            fail(f"Expected 404 (or 403) for non-existent user. Got {r.status_code}. Body: {(r.text or '').strip()}")

        # 6) Invalid choice (0 or 5) => 422
        await req(client, "POST", vote_url, 422, json={"user_id": user_reg_id, "choice": 0})
        await req(client, "POST", vote_url, 422, json={"user_id": user_reg_id, "choice": 5})
        ok("Invalid choice blocked with 422")

        # 7) Create vote => 201/200
        created_vote = await req(client, "POST", vote_url, (200, 201), json={"user_id": user_reg_id, "choice": 1})
        vote_id = pick_id(created_vote, "vote_id", "id")
        ok(f"Created vote OK (vote_id={vote_id})")

        # 8) Duplicate vote => 409
        await req(client, "POST", vote_url, 409, json={"user_id": user_reg_id, "choice": 2})
        ok("Duplicate vote blocked with 409")

        # 9) Update vote (PUT) => 200
        # Try PUT on the same url; if 405, try alternate path
        r = await client.put(vote_url, json={"user_id": user_reg_id, "choice": 3})
        if r.status_code == 405:
            alt = vote_url.replace("/vote", "/votes") if vote_url.endswith("/vote") else vote_url.replace("/votes", "/vote")
            r2 = await client.put(alt, json={"user_id": user_reg_id, "choice": 3})
            if r2.status_code not in (200, 201):
                fail(f"Vote update failed on both endpoints. Got {r.status_code} and {r2.status_code}.")
        elif r.status_code not in (200, 201):
            fail(f"Expected 200/201 for vote update. Got {r.status_code}. Body: {(r.text or '').strip()}")
        ok("Vote update OK")

        # 10) Internal endpoint security (key)
        internal_url = f"{POLL_BASE_URL}/internal/users/{user_reg_id}/votes"

        await req(client, "DELETE", internal_url, 401)
        ok("Internal endpoint without key blocked with 401")

        await req(client, "DELETE", internal_url, 401, headers={"X-Internal-Key": "wrong-key"})
        ok("Internal endpoint with wrong key blocked with 401")

        await req(client, "DELETE", internal_url, (200, 204), headers={"X-Internal-Key": INTERNAL_API_KEY})
        ok("Internal endpoint with correct key OK (votes deleted)")

        # 11) After internal deletion: update vote should be 404 (vote not found)
        r = await client.put(vote_url, json={"user_id": user_reg_id, "choice": 2})
        if r.status_code != 404:
            warn(f"Expected 404 after internal delete on update vote. Got {r.status_code} (check your implementation).")
        else:
            ok("After internal delete: vote update returns 404")

        # 12) Delete user should cascade delete votes in poll-service
        # Create a fresh registered user, vote, then delete user and ensure future votes block with 404/403.
        u2 = await req(
            client,
            "POST",
            f"{USER_BASE_URL}/users",
            (200, 201),
            json={
                "first_name": "Test",
                "last_name": "Cascade",
                "email": f"cascade_{unique}@example.com",
                "age": 22,
                "address": "Somewhere",
            },
        )
        user2_id = pick_id(u2, "id", "user_id")
        await req(client, "POST", f"{USER_BASE_URL}/users/{user2_id}/register", (200, 201))
        ok(f"Created+registered user2 user_id={user2_id}")

        await req(client, "POST", vote_url, (200, 201), json={"user_id": user2_id, "choice": 4})
        ok("Created vote for user2 OK")

        await req(client, "DELETE", f"{USER_BASE_URL}/users/{user2_id}", (200, 204))
        ok("Deleted user2 OK (should cascade delete votes in poll-service)")

        r = await client.post(vote_url, json={"user_id": user2_id, "choice": 1})
        if r.status_code == 404:
            ok("After deleting user2: poll-service blocks voting with 404 (User not found)")
        elif r.status_code == 403:
            warn("After deleting user2: poll-service returned 403 (acceptable if you treat as not-allowed).")
        else:
            fail(f"After deleting user2: expected 404/403. Got {r.status_code}. Body: {(r.text or '').strip()}")

    print("\n🎉 INTEGRATION PREFLIGHT PASSED ✅")


if __name__ == "__main__":
    asyncio.run(main())
