from repository.database import database


async def get_user_vote_for_question(user_id: int, question_id: int):
    query = """
        SELECT vote_id, question_id, user_id, choice, created_at
        FROM votes
        WHERE user_id = :user_id AND question_id = :question_id
    """
    row = await database.fetch_one(
        query=query,
        values={"user_id": int(user_id), "question_id": int(question_id)},
    )
    return dict(row) if row else None


async def get_vote_by_id(vote_id: int):
    query = """
        SELECT vote_id, question_id, user_id, choice, created_at
        FROM votes
        WHERE vote_id = :vote_id
    """
    row = await database.fetch_one(query=query, values={"vote_id": int(vote_id)})
    return dict(row) if row else None


async def create_vote(question_id: int, user_id: int, choice: int):
    query = """
        INSERT INTO votes (question_id, user_id, choice)
        VALUES (:question_id, :user_id, :choice)
    """
    vote_id = await database.execute(
        query=query,
        values={"question_id": int(question_id), "user_id": int(user_id), "choice": int(choice)},
    )
    return await get_vote_by_id(int(vote_id))


async def update_vote_choice(vote_id: int, choice: int):
    query = """
        UPDATE votes
        SET choice = :choice
        WHERE vote_id = :vote_id
    """
    await database.execute(query=query, values={"vote_id": int(vote_id), "choice": int(choice)})
    return await get_vote_by_id(int(vote_id))


async def delete_votes_by_user_id(user_id: int) -> int:
    query = "DELETE FROM votes WHERE user_id = :user_id"
    result = await database.execute(query=query, values={"user_id": int(user_id)})
    # databases may return number of rows or lastrowid; keep simple
    return int(result) if isinstance(result, int) else 0


async def results_for_question(question_id: int):
    """
    Always returns 4 rows (choice 1..4), with votes = 0 if no votes.
    """
    query = """
        SELECT c.choice AS choice, COALESCE(v.votes, 0) AS votes
        FROM (
            SELECT 1 AS choice
            UNION ALL SELECT 2
            UNION ALL SELECT 3
            UNION ALL SELECT 4
        ) c
        LEFT JOIN (
            SELECT choice, COUNT(*) AS votes
            FROM votes
            WHERE question_id = :question_id
            GROUP BY choice
        ) v
        ON v.choice = c.choice
        ORDER BY c.choice ASC
    """
    rows = await database.fetch_all(query=query, values={"question_id": int(question_id)})
    return [dict(r) for r in rows]


async def total_votes_for_question(question_id: int) -> int:
    query = "SELECT COUNT(*) AS cnt FROM votes WHERE question_id = :question_id"
    row = await database.fetch_one(query=query, values={"question_id": int(question_id)})
    return int(row["cnt"]) if row else 0
