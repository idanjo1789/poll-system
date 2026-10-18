import asyncio
import httpx


BASE_URL = "http://localhost:8002"


def ok(msg):
    print(f"✅ {msg}")


def fail(msg):
    print(f"\n❌ {msg}")
    raise SystemExit(1)


async def main():
    print("=== Runtime integration test: poll-service ===")

    async with httpx.AsyncClient(timeout=5.0) as client:

        # 1️⃣ Health
        r = await client.get(f"{BASE_URL}/health")
        if r.status_code != 200:
            fail("Health endpoint failed")
        ok("Health OK")

        # 2️⃣ Create question
        r = await client.post(
            f"{BASE_URL}/questions",
            json={
                "title": "Best language?",
                "description": "Choose one",
                "is_active": True,
            },
        )
        if r.status_code != 201:
            fail("Create question failed")

        question = r.json()
        question_id = question["question_id"]
        ok(f"Question created (id={question_id})")

        # 3️⃣ Create 4 answers
        answers = ["Python", "Java", "C++", "Go"]
        for a in answers:
            r = await client.post(
                f"{BASE_URL}/questions/{question_id}/answers",
                json={"text": a},
            )
            if r.status_code != 201:
                fail("Creating answer failed")

        ok("4 answers created")

        # 4️⃣ Try creating 5th answer → should fail
        r = await client.post(
            f"{BASE_URL}/questions/{question_id}/answers",
            json={"text": "Rust"},
        )
        if r.status_code != 409:
            fail("5th answer should fail with 409")
        ok("Answer limit enforcement OK")

        # 5️⃣ Get results (no votes yet)
        r = await client.get(f"{BASE_URL}/questions/{question_id}/results")
        if r.status_code != 200:
            fail("Results endpoint failed")

        results = r.json()
        if results["total_votes"] != 0:
            fail("Total votes should be 0")

        ok("Results endpoint OK")

    print("\n🎉 Runtime test passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
