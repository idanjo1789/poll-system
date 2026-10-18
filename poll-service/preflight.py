# poll-service/preflight.py
import asyncio
import compileall
import sys
import traceback
from urllib.parse import urlparse

import httpx


def fail(msg: str) -> None:
    print(f"\n❌ {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"⚠️  {msg}")


def ok(msg: str) -> None:
    print(f"✅ {msg}")


async def main() -> None:
    print("=== Preflight checks: poll-service ===")

    # 1) Syntax / compilation check
    # Compile project folders (new structure)
    folders = ["config", "controller", "model", "repository", "service"]
    for f in folders:
        if not compileall.compile_dir(f, quiet=1):
            fail(f"Compilation failed (syntax errors) in {f}/")
    ok("Python compilation (syntax) OK")

    # 2) Import check (new imports)
    try:
        from config.config import DATABASE_URL, USER_SERVICE_BASE_URL, INTERNAL_API_KEY  # noqa
        from repository.database import database  # noqa
        from main import app  # noqa
    except Exception:
        traceback.print_exc()
        fail("Import failed. Check folder names, __init__.py, and PYTHONPATH.")
    ok("Imports OK (config/database/main)")

    # 3) Basic config validation
    from config.config import DATABASE_URL, USER_SERVICE_BASE_URL, INTERNAL_API_KEY

    parsed = urlparse(DATABASE_URL)
    if not parsed.scheme.startswith("mysql"):
        fail(f"DATABASE_URL doesn't look like MySQL URL: {DATABASE_URL}")
    ok("DATABASE_URL looks valid")

    ok(f"USER_SERVICE_BASE_URL = {USER_SERVICE_BASE_URL}")

    if not INTERNAL_API_KEY or INTERNAL_API_KEY == "change-me":
        warn("INTERNAL_API_KEY is missing or default (change-me). Internal delete may be insecure/fail.")

    # 4) DB connectivity + tables exist
    from repository.database import database

    try:
        await database.connect()
        ok("Connected to DB")
    except Exception:
        traceback.print_exc()
        fail("Failed to connect to DB. Check DB_HOST/DB_USER/DB_PASSWORD/DB_NAME and DB is up.")

    required_tables = {"questions", "answers", "votes"}
    try:
        rows = await database.fetch_all(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
        )
        existing = {r["table_name"] for r in rows}
        missing = sorted(list(required_tables - existing))
        if missing:
            fail(f"Missing DB tables: {missing}. Did you run the SQL files?")
        ok("All required tables exist (questions, answers, votes)")
    except Exception:
        traceback.print_exc()
        fail("Failed to query information_schema. Check DB permissions.")

    # 5) Optional: user-service reachable (won't fail the whole preflight)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{USER_SERVICE_BASE_URL.rstrip('/')}/health")
        if r.status_code < 400:
            ok("user-service reachable (/health)")
        else:
            warn(f"user-service /health returned status {r.status_code} (vote may fail on user check)")
    except Exception:
        warn("user-service not reachable (vote endpoints may fail if you enforce user existence)")

    await database.disconnect()
    ok("Disconnected from DB")
    print("\n🎉 Preflight passed. You can start uvicorn safely.")


if __name__ == "__main__":
    asyncio.run(main())