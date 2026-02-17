from repository.database import database


async def create_question(title: str, description: str | None, is_active: bool):
    query = """
        INSERT INTO questions (title, description, is_active)
        VALUES (:title, :description, :is_active)
    """
    question_id = await database.execute(
        query=query,
        values={
            "title": title,
            "description": description,
            "is_active": int(is_active),
        },
    )
    return await get_question_by_id(question_id)


async def get_question_by_id(question_id: int):
    query = """
        SELECT question_id, title, description, is_active, created_at
        FROM questions
        WHERE question_id = :question_id
    """
    row = await database.fetch_one(
        query=query,
        values={"question_id": question_id},
    )
    return dict(row) if row else None


async def list_questions(limit: int = 50, offset: int = 0):
    query = """
        SELECT question_id, title, description, is_active, created_at
        FROM questions
        ORDER BY question_id DESC
        LIMIT :limit OFFSET :offset
    """
    rows = await database.fetch_all(
        query=query,
        values={"limit": limit, "offset": offset},
    )
    return [dict(r) for r in rows]


async def count_questions():
    query = "SELECT COUNT(*) AS cnt FROM questions"
    row = await database.fetch_one(query=query)
    return int(row["cnt"]) if row else 0


async def update_question(question_id: int, title: str | None, description: str | None, is_active: bool | None):
    set_parts = []
    values = {"question_id": question_id}

    if title is not None:
        set_parts.append("title = :title")
        values["title"] = title

    if description is not None:
        set_parts.append("description = :description")
        values["description"] = description

    if is_active is not None:
        set_parts.append("is_active = :is_active")
        values["is_active"] = int(is_active)

    if not set_parts:
        return None

    query = f"""
        UPDATE questions
        SET {", ".join(set_parts)}
        WHERE question_id = :question_id
    """

    await database.execute(query=query, values=values)
    return await get_question_by_id(question_id)


async def delete_question(question_id: int):
    query = "DELETE FROM questions WHERE question_id = :question_id"
    await database.execute(query=query, values={"question_id": question_id})
    return True
