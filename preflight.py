# poll-service/preflight.py
import asyncio
import compileall
import sys
import traceback
from urllib.parse import urlparse

import httpx

from repository.database import database 



def fail(msg: str) -> None:
    print(f"\n❌ {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"⚠️  {msg}")


def ok(msg: str) -> None:
    print(f"✅ {msg}")


async def main() -> None:
    print("=== Preflight checks: poll-service ===")

    # 1) Syntax
    if not compileall.compile_dir("app", quiet=1):
        fail("Compilation failed (syntax errors) in app/")
    ok("Python compilation (syntax) OK")

    # 2) Imports
    try:
        from app.config import DATABASE_URL, USER_SERVICE_BASE_URL, SERVICE_NAME  # noqa
        from app.main import app  # noqa
    except Exception:
        traceback.print_exc()
        fail("Import failed. Check module paths.")
    ok("Imports OK (config/main)")

    # 3) Config
    ok(f"SERVICE_NAME = {SERVICE_NAME}")

    parsed = urlparse(DATABASE_URL)
    if not parsed.scheme.startswith("mysql"):
        fail(f"DATABASE_URL doesn't look like MySQL URL: {DATABASE_URL}")
    ok("DATABASE_URL looks valid")

    ok(f"USER_SERVICE_BASE_URL = {USER_SERVICE_BASE_URL}")

    # 4) DB connect

    try:
        await database.connect()
        ok("Connected to DB")

        # Check required tables
        required_tables = {"questions", "answers", "votes"}
        rows = await database.fetch_all(
            "SELECT table_name AS name FROM information_schema.tables WHERE table_schema = DATABASE()"
        )
        existing = {r["name"] for r in rows}
        missing = sorted(list(required_tables - existing))
        if missing:
            fail(f"Missing DB tables: {missing}. Did you run the SQL files?")
        ok("All required tables exist (questions, answers, votes)")

        # 5) Optional: check user-service reachable (won't fail the whole preflight)
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{USER_SERVICE_BASE_URL.rstrip('/')}/health")
            if r.status_code < 400:
                ok("user-service reachable (/health)")
            else:
                warn(f"user-service /health returned status {r.status_code} (vote may fail on user check)")
        except Exception:
            warn("user-service not reachable (vote endpoint may fail if you enforce user existence)")

    except Exception:
        traceback.print_exc()
        fail("Preflight failed during DB/table checks.")
    finally:
        try:
            await database.disconnect()
            ok("Disconnected from DB")
        except Exception:
            pass

    print("\n🎉 Preflight passed. You can start uvicorn safely.")
    return

    # 5) tables exist
    required_tables = {"questions", "answers", "votes"}
    try:
        rows = await database.fetch_all(
            """
            SELECT table_name AS name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            """
        )
        existing = {dict(r)["name"] for r in rows}
        missing = sorted(list(required_tables - existing))
        if missing:
            fail(f"Missing DB tables: {missing}. Did you run the SQL files?")
        ok("All required tables exist (questions, answers, votes)")
    except Exception:
        traceback.print_exc()
        fail("Failed to query information_schema")

    # 6) user-service reachable (optional)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{USER_SERVICE_BASE_URL.rstrip('/')}/health")
        if r.status_code < 400:
            ok("user-service reachable (/health)")
        else:
            warn(f"user-service /health returned {r.status_code}")
    except Exception:
        warn("user-service not reachable (vote may fail if you enforce user existence)")

    await database.disconnect()
    ok("Disconnected from DB")
    print("\n🎉 poll-service preflight passed.")


if __name__ == "__main__":
    asyncio.run(main())
