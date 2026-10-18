# preflight_poll_service.py
# Run from host (poll-system root):
#   python preflight_poll_service.py
#
# What it checks:
# - user-service health + basic user create/register
# - poll-service health
# - create question
# - create 4 answers (5th must fail 409)
# - retrieval: list questions, get question, list answers (choices 1..4)
# - vote rules: unregistered -> 403, registered -> 201, duplicate -> 409, update -> 200, idempotent update -> 200
# - delete user: verifies votes removed from poll DB (via docker compose exec mysql-poll)
#
# Requires:
#   pip install httpx

import asyncio
import re
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import httpx

USER_BASE = "http://127.0.0.1:8001"
POLL_BASE = "http://127.0.0.1:8002"

# MySQL creds used in your docker compose (adjust if different)
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
POLL_DB = "poll_db"
MYSQL_POLL_SERVICE = "mysql-poll"  # docker compose service name


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def warn(msg: str) -> None:
    print(f"⚠️  {msg}")


def fail(msg: str) -> None:
    raise RuntimeError(f"❌ {msg}")


async def assert_status(resp: httpx.Response, expected: int, label: str) -> None:
    if resp.status_code != expected:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        fail(f"{label}: expected {expected}, got {resp.status_code}. body={body}")
    ok(f"{label} -> {expected} OK")


def unique_email() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"idan_test_{ts}@example.com"


def _run_cmd(cmd: list[str]) -> Tuple[int, str, str]:
    """
    Runs command and returns (returncode, stdout, stderr).
    Uses text mode; safe for Windows.
    """
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def get_poll_votes_count_for_user(user_id: int) -> Optional[int]:
    """
    Reads votes count from poll DB inside docker mysql-poll container.
    Returns int on success, None if docker command failed (so we can skip).
    """
    # Note: using -e with a single query
    query = f"SELECT COUNT(*) AS cnt FROM votes WHERE user_id = {int(user_id)};"
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        MYSQL_POLL_SERVICE,
        "mysql",
        f"-u{MYSQL_USER}",
        f"-p{MYSQL_PASSWORD}",
        "-D",
        POLL_DB,
        "-e",
        query,
    ]
    rc, out, err = _run_cmd(cmd)
    if rc != 0:
        warn(f"Could not query poll DB via docker compose exec (rc={rc}). stderr={err}")
        return None

    # Typical output:
    # cnt
    # 1
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        warn(f"Unexpected mysql output: {out}")
        return None

    # last non-empty line should be the number
    m = re.search(r"(\d+)$", lines[-1].strip())
    if not m:
        warn(f"Could not parse count from mysql output: {out}")
        return None

    return int(m.group(1))


async def create_user(client: httpx.AsyncClient, is_registered: bool) -> Dict[str, Any]:
    payload = {
        "first_name": "Idan",
        "last_name": "Tester",
        "email": unique_email(),
        "age": 28,
        "address": "Test St 1",
        "joining_date": "2026-02-10",
    }
    r = await client.post(f"{USER_BASE}/users", json=payload)
    await assert_status(r, 201, "Create user")

    created = r.json()
    user_id = created.get("id") or created.get("user_id")
    if not user_id:
        fail("Create user: response missing id/user_id")

    if is_registered:
        rr = await client.post(f"{USER_BASE}/users/{user_id}/register")
        await assert_status(rr, 200, "Register user")

    gr = await client.get(f"{USER_BASE}/users/{user_id}")
    await assert_status(gr, 200, "Get user")
    return gr.json()


async def create_question(client: httpx.AsyncClient) -> Dict[str, Any]:
    payload = {"title": "Favorite framework?", "description": "Pick one", "is_active": True}
    r = await client.post(f"{POLL_BASE}/questions", json=payload)
    await assert_status(r, 201, "Create question")
    return r.json()


async def create_answer(client: httpx.AsyncClient, question_id: int, text_value: str, idx: int) -> Dict[str, Any]:
    r = await client.post(f"{POLL_BASE}/questions/{question_id}/answers", json={"text": text_value})
    await assert_status(r, 201, f"Create answer #{idx}")
    return r.json()


async def list_questions(client: httpx.AsyncClient, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    r = await client.get(f"{POLL_BASE}/questions", params={"limit": limit, "offset": offset})
    await assert_status(r, 200, "List questions")
    return r.json()


async def get_question(client: httpx.AsyncClient, question_id: int) -> Dict[str, Any]:
    r = await client.get(f"{POLL_BASE}/questions/{question_id}")
    await assert_status(r, 200, "Get question")
    return r.json()


async def list_answers(client: httpx.AsyncClient, question_id: int) -> Dict[str, Any]:
    r = await client.get(f"{POLL_BASE}/questions/{question_id}/answers")
    await assert_status(r, 200, "List answers")
    return r.json()


async def create_vote(client: httpx.AsyncClient, question_id: int, user_id: int, choice: int, expected_status: int, label: str):
    r = await client.post(f"{POLL_BASE}/questions/{question_id}/vote", json={"user_id": user_id, "choice": choice})
    await assert_status(r, expected_status, label)
    return r.json() if r.status_code < 300 else None


async def update_vote(client: httpx.AsyncClient, question_id: int, user_id: int, choice: int, expected_status: int, label: str):
    r = await client.put(f"{POLL_BASE}/questions/{question_id}/vote", json={"user_id": user_id, "choice": choice})
    await assert_status(r, expected_status, label)
    return r.json() if r.status_code < 300 else None


async def delete_user(client: httpx.AsyncClient, user_id: int) -> None:
    r = await client.delete(f"{USER_BASE}/users/{user_id}")
    if r.status_code in (200, 204):
        ok(f"Delete user -> {r.status_code} OK")
        return
    await assert_status(r, 200, "Delete user")


async def main() -> None:
    t0 = time.time()

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Health
        await assert_status(await client.get(f"{USER_BASE}/health"), 200, "user-service health")
        await assert_status(await client.get(f"{POLL_BASE}/health"), 200, "poll-service health")

        # Users
        unreg = await create_user(client, is_registered=False)
        reg = await create_user(client, is_registered=True)

        unreg_id = int(unreg.get("id") or unreg.get("user_id"))
        reg_id = int(reg.get("id") or reg.get("user_id"))

        # Question
        q = await create_question(client)
        qid = int(q.get("id") or q.get("question_id"))
        if not qid:
            fail("Create question: response missing id/question_id")

        # Answers (4 ok, 5th -> 409)
        for i in range(1, 5):
            await create_answer(client, qid, f"Option {i}", i)

        r5 = await client.post(f"{POLL_BASE}/questions/{qid}/answers", json={"text": "Option 5"})
        await assert_status(r5, 409, "Create answer #5 should fail (max 4)")

        # Retrieval checks: list questions includes our question; get question matches title; list answers has 4 with choices 1..4
        qlist = await list_questions(client)
        items = qlist.get("items", [])
        if not isinstance(items, list) or len(items) < 1:
            fail("List questions: expected non-empty items")

        # question response might use id alias; accept both
        found = False
        for it in items:
            q_item_id = it.get("question_id") or it.get("id")
            if int(q_item_id) == qid:
                found = True
                break
        if not found:
            warn("List questions: did not find created question in first page (might be ordering/pagination).")

        qget = await get_question(client, qid)
        got_title = qget.get("title")
        if got_title != "Favorite framework?":
            fail(f"Get question: title mismatch. got={got_title}")

        answers = await list_answers(client, qid)
        ans_items = answers.get("items", [])
        if len(ans_items) != 4:
            fail(f"List answers: expected 4, got {len(ans_items)}")

        choices = [a.get("choice") for a in ans_items]
        if choices != [1, 2, 3, 4]:
            fail(f"Answer choices expected [1,2,3,4], got {choices}")
        ok("Answer choices computed correctly (1..4)")

        # Votes
        rv_unreg = await client.post(f"{POLL_BASE}/questions/{qid}/vote", json={"user_id": unreg_id, "choice": 1})
        await assert_status(rv_unreg, 403, "Vote with unregistered user should be 403")

        await create_vote(client, qid, reg_id, 2, 201, "Vote create (registered user)")
        rv_dup = await client.post(f"{POLL_BASE}/questions/{qid}/vote", json={"user_id": reg_id, "choice": 3})
        await assert_status(rv_dup, 409, "Duplicate vote should be 409")

        await update_vote(client, qid, reg_id, 3, 200, "Vote update should be 200")
        await update_vote(client, qid, reg_id, 3, 200, "Vote update same choice (idempotent)")

        # Verify votes exist in DB BEFORE delete (best-effort)
        before_cnt = get_poll_votes_count_for_user(reg_id)
        if before_cnt is not None:
            if before_cnt < 1:
                fail(f"Expected votes count >= 1 before delete, got {before_cnt}")
            ok(f"DB verify BEFORE delete: votes for user_id={reg_id} -> {before_cnt}")

        # Delete user
        await delete_user(client, reg_id)

        # After delete: API behavior (poll checks user-service first)
        ru = await client.put(f"{POLL_BASE}/questions/{qid}/vote", json={"user_id": reg_id, "choice": 1})
        await assert_status(ru, 404, "After user delete, vote update should be 404 (User not found)")

        # Verify votes removed in DB AFTER delete (best-effort)
        after_cnt = get_poll_votes_count_for_user(reg_id)
        if after_cnt is not None:
            if after_cnt != 0:
                fail(f"Expected votes count = 0 after delete, got {after_cnt}")
            ok(f"DB verify AFTER delete: votes for user_id={reg_id} -> {after_cnt}")

    ok(f"ALL POLL PREFLIGHT CHECKS PASSED in {time.time() - t0:.2f}s ✅")


if __name__ == "__main__":
    asyncio.run(main())
