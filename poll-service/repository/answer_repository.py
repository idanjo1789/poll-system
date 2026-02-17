from repository.database import database


async def create_answer(question_id: int, choice: int, text_value: str):
    query = """
        INSERT INTO answers (question_id, choice, text)
        VALUES (:question_id, :choice, :text)
    """
    answer_id = await database.execute(
        query=query,
        values={"question_id": int(question_id), "choice": int(choice), "text": text_value},
    )
    return await get_answer_by_id(int(answer_id))


async def get_answer_by_id(answer_id: int):
    query = """
        SELECT answer_id, question_id, choice, text, created_at
        FROM answers
        WHERE answer_id = :answer_id
    """
    row = await database.fetch_one(query=query, values={"answer_id": int(answer_id)})
    return dict(row) if row else None


async def list_answers_by_question(question_id: int, limit: int = 200, offset: int = 0):
    query = """
        SELECT answer_id, question_id, choice, text, created_at
        FROM answers
        WHERE question_id = :question_id
        ORDER BY choice ASC
        LIMIT :limit OFFSET :offset
    """
    rows = await database.fetch_all(
        query=query,
        values={"question_id": int(question_id), "limit": int(limit), "offset": int(offset)},
    )
    return [dict(r) for r in rows]


async def list_choices_by_question(question_id: int):
    query = """
        SELECT choice
        FROM answers
        WHERE question_id = :question_id
        ORDER BY choice ASC
    """
    rows = await database.fetch_all(query=query, values={"question_id": int(question_id)})
    return [int(r["choice"]) for r in rows]


async def count_answers_by_question(question_id: int) -> int:
    query = "SELECT COUNT(*) AS cnt FROM answers WHERE question_id = :question_id"
    row = await database.fetch_one(query=query, values={"question_id": int(question_id)})
    return int(row["cnt"]) if row else 0


async def delete_answer(answer_id: int):
    query = "DELETE FROM answers WHERE answer_id = :answer_id"
    await database.execute(query=query, values={"answer_id": int(answer_id)})
    return True
