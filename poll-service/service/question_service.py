from repository import question_repository


async def create_question(title: str, description: str | None, is_active: bool):
    return await question_repository.create_question(
        title=title,
        description=description,
        is_active=is_active,
    )


async def get_question(question_id: int):
    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None
    return question


async def list_questions(limit: int = 50, offset: int = 0):
    items = await question_repository.list_questions(limit=limit, offset=offset)
    total = await question_repository.count_questions()

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def update_question(question_id: int, title: str | None, description: str | None, is_active: bool | None):
    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None

    return await question_repository.update_question(
        question_id=question_id,
        title=title,
        description=description,
        is_active=is_active,
    )


async def delete_question(question_id: int):
    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None

    await question_repository.delete_question(question_id)
    return True
