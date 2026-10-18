# integration_preflight_v2_fixed.py
# Run from project root (host):
#   python .\integration_preflight_v2_fixed.py
#
# Env overrides (optional):
#   USER_BASE_URL=http://127.0.0.1:8001
#   POLL_BASE_URL=http://127.0.0.1:8002
#   INTERNAL_API_KEY=super-secret-key

import asyncio
import os
import uuid
from typing import Any, Iterable, Optional, Tuple, Union, List

import httpx

USER_BASE_URL = os.getenv("USER_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
POLL_BASE_URL = os.getenv("POLL_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "").strip()


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def info(msg: str) -> None:
    print(f"ℹ️  {msg}")


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


def pick_int(d: dict, keys: List[str]) -> int:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        try:
            return int(v)
        except Exception:
            pass
    fail(f"Could not find int id in response. Keys tried={keys}. Response={d}")


async def req_first_ok(
    client: httpx.AsyncClient,
    method: str,
    urls: List[str],
    expected: ExpectedType,
    *,
    json: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> Any:
    # Try multiple URLs; return first that matches expected codes.
    last_err = None
    for url in urls:
        try:
            return await req(client, method, url, expected, json=json, headers=headers)
        except Exception as e:
            last_err = e
    raise last_err  # type: ignore[misc]


async def main() -> None:
    print("=== Integration Preflight v2: user-service <-> poll-service ===")
    print(f"USER_BASE_URL = {USER_BASE_URL}")
    print(f"POLL_BASE_URL = {POLL_BASE_URL}")
    print(f"INTERNAL_API_KEY = {'***' if INTERNAL_API_KEY else '(empty)'}\n")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 0) Health checks
        await req(client, "GET", f"{USER_BASE_URL}/health", 200)
        ok("user-service /health OK")

        await req(client, "GET", f"{POLL_BASE_URL}/health", 200)
        ok("poll-service /health OK")

        unique = uuid.uuid4().hex[:8]

        # Create NOT-registered user (NOTE: no joining_date in payload)
        user_unreg_payload = {
            "first_name": "Test",
            "last_name": "Unreg",
            "email": f"unreg_{unique}@example.com",
            "age": 30,
            "address": "Somewhere",
        }
        u_unreg = await req(client, "POST", f"{USER_BASE_URL}/users", (200, 201), json=user_unreg_payload)
        user_unreg_id = pick_int(u_unreg, ["id", "user_id"])
        ok(f"Created user (NOT registered) user_id={user_unreg_id}")

        # Create user to register
        user_reg_payload = {
            "first_name": "Test",
            "last_name": "Reg",
            "email": f"reg_{unique}@example.com",
            "age": 31,
            "address": "Somewhere",
        }
        u_reg = await req(client, "POST", f"{USER_BASE_URL}/users", (200, 201), json=user_reg_payload)
        user_reg_id = pick_int(u_reg, ["id", "user_id"])
        ok(f"Created user (to register) user_id={user_reg_id}")

        await req(client, "POST", f"{USER_BASE_URL}/users/{user_reg_id}/register", (200, 201))
        ok("User registered OK")

        # Create question
        q_payload = {"title": f"Question {unique}", "description": "Integration test", "is_active": True}
        q = await req(client, "POST", f"{POLL_BASE_URL}/questions", (200, 201), json=q_payload)
        question_id = pick_int(q, ["question_id", "id"])
        ok(f"Created question question_id={question_id}")

        # Create 4 answers
        for i in range(1, 5):
            a_payload = {"text": f"Answer {i}"}
            await req(client, "POST", f"{POLL_BASE_URL}/questions/{question_id}/answers", (200, 201), json=a_payload)
        ok("Created 4 answers OK")

        # Helper: vote endpoint may be /questions/{id}/vote OR /votes
        def vote_urls(qid: int) -> List[str]:
            return [
                f"{POLL_BASE_URL}/questions/{qid}/vote",
                f"{POLL_BASE_URL}/votes",
            ]

        def vote_payload(user_id: int, choice: int, qid: int) -> dict:
            # /questions/{qid}/vote usually needs no question_id in body, but /votes may need it.
            # We'll include question_id to be safe; services that don't need it should ignore it (or you can remove if 422).
            return {"user_id": user_id, "choice": choice, "question_id": qid}

        # 1) Unregistered user cannot vote => 403
        await req_first_ok(
            client, "POST", vote_urls(question_id), 403, json=vote_payload(user_unreg_id, 2, question_id)
        )
        ok("Unregistered user voting blocked with 403")

        # 2) Non-existent user => 404
        non_exist_user_id = 99999999
        await req_first_ok(
            client, "POST", vote_urls(question_id), 404, json=vote_payload(non_exist_user_id, 2, question_id)
        )
        ok("Non-existent user voting blocked with 404")

        # 3) Invalid choice => 422
        await req_first_ok(
            client, "POST", vote_urls(question_id), 422, json=vote_payload(user_reg_id, 0, question_id)
        )
        await req_first_ok(
            client, "POST", vote_urls(question_id), 422, json=vote_payload(user_reg_id, 5, question_id)
        )
        ok("Invalid choice blocked with 422")

        # 4) Duplicate vote => first 201/200, second 409
        created_vote = await req_first_ok(
            client, "POST", vote_urls(question_id), (200, 201), json=vote_payload(user_reg_id, 1, question_id)
        )
        vote_id = pick_int(created_vote, ["vote_id", "id"])
        ok(f"Created vote OK (vote_id={vote_id})")

        await req_first_ok(
            client, "POST", vote_urls(question_id), 409, json=vote_payload(user_reg_id, 2, question_id)
        )
        ok("Duplicate vote blocked with 409")

        # 5) Update before create => 404 (create fresh user+question)
        u2 = await req(
            client,
            "POST",
            f"{USER_BASE_URL}/users",
            (200, 201),
            json={
                "first_name": "Test",
                "last_name": "UpdBeforeCreate",
                "email": f"u2_{unique}@example.com",
                "age": 22,
                "address": "Somewhere",
            },
        )
        user2_id = pick_int(u2, ["id", "user_id"])
        await req(client, "POST", f"{USER_BASE_URL}/users/{user2_id}/register", (200, 201))
        ok(f"Created+registered user2 user_id={user2_id}")

        q2 = await req(
            client,
            "POST",
            f"{POLL_BASE_URL}/questions",
            (200, 201),
            json={"title": f"Question2 {unique}", "description": "Integration test", "is_active": True},
        )
        question2_id = pick_int(q2, ["question_id", "id"])
        for i in range(1, 5):
            await req(
                client,
                "POST",
                f"{POLL_BASE_URL}/questions/{question2_id}/answers",
                (200, 201),
                json={"text": f"Q2 Answer {i}"},
            )
        ok(f"Created question2 + 4 answers (question_id={question2_id})")

        # update endpoint might be /questions/{id}/vote (PUT) OR /votes (PUT) depending on your API
        update_urls = [
            f"{POLL_BASE_URL}/questions/{question2_id}/vote",
            f"{POLL_BASE_URL}/votes",
        ]
        await req_first_ok(
            client, "PUT", update_urls, 404, json={"user_id": user2_id, "choice": 3, "question_id": question2_id}
        )
        ok("Update before create blocked with 404")

        # 6) 5th answer => 409
        await req(
            client,
            "POST",
            f"{POLL_BASE_URL}/questions/{question_id}/answers",
            409,
            json={"text": "Answer 5 (should fail)"},
        )
        ok("5th answer blocked with 409")

        # 7) Delete question cascades answers + votes
        await req(client, "DELETE", f"{POLL_BASE_URL}/questions/{question_id}", (200, 204))
        ok("Deleted question OK")

        await req(
            client,
            "POST",
            f"{POLL_BASE_URL}/questions/{question_id}/answers",
            404,
            json={"text": "Should fail because question deleted"},
        )
        ok("After question delete: cannot create answers (404)")

        await req_first_ok(
            client,
            "PUT",
            update_urls,
            404,
            json={"user_id": user_reg_id, "choice": 2, "question_id": question_id},
        )
        ok("After question delete: vote update returns 404 (vote not found)")

        # 8) Internal endpoint security
        internal_url = f"{POLL_BASE_URL}/internal/users/{user2_id}/votes"

        await req(client, "DELETE", internal_url, 401)
        ok("Internal endpoint without key blocked with 401")

        await req(client, "DELETE", internal_url, 401, headers={"X-Internal-Key": "wrong-key"})
        ok("Internal endpoint with wrong key blocked with 401")

        if not INTERNAL_API_KEY:
            info("INTERNAL_API_KEY is empty in environment; skipping 'correct key' internal test.")
        else:
            await req(client, "DELETE", internal_url, 200, headers={"X-Internal-Key": INTERNAL_API_KEY})
            ok("Internal endpoint with correct key OK (200)")

        # Bonus: Delete user cascades votes
        v2 = await req_first_ok(
            client,
            "POST",
            vote_urls(question2_id),
            (200, 201),
            json=vote_payload(user2_id, 1, question2_id),
        )
        ok(f"Created vote2 OK (vote_id={pick_int(v2, ['vote_id', 'id'])})")

        await req(client, "DELETE", f"{USER_BASE_URL}/users/{user2_id}", (200, 204))
        ok("Deleted user2 OK (should cascade delete votes in poll-service)")

        await req_first_ok(
            client, "POST", vote_urls(question2_id), 404, json=vote_payload(user2_id, 2, question2_id)
        )
        ok("After deleting user2: poll-service blocks voting with 404 (User not found)")

    print("\n🎉 INTEGRATION PREFLIGHT v2 PASSED ✅")


if __name__ == "__main__":
    asyncio.run(main())
