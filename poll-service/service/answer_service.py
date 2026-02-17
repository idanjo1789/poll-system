from repository import answer_repository
from repository import question_repository
from repository import vote_repository


async def create_answer_for_question(question_id: int, text_value: str):
    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None, "Question not found"

    if text_value is None or not str(text_value).strip():
        return None, "Answer text is required"


    current_count = await answer_repository.count_answers_by_question(question_id)
    if current_count >= 4:
        return None, "Question already has 4 answers"


    used = set(await answer_repository.list_choices_by_question(question_id))
    available = [c for c in (1, 2, 3, 4) if c not in used]
    if not available:
        return None, "Question already has 4 answers"

    choice = available[0]

    created = await answer_repository.create_answer(
        question_id=question_id,
        choice=choice,
        text_value=str(text_value).strip(),
    )
    if not created:
        return None, "Failed to create answer"

    return created, None


async def list_answers_for_question(question_id: int, limit: int = 200, offset: int = 0):
    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None, "Question not found"

    items = await answer_repository.list_answers_by_question(question_id, limit=limit, offset=offset)
    total = await answer_repository.count_answers_by_question(question_id)

    return {"items": items, "total": total, "limit": limit, "offset": offset}, None


async def delete_answer(answer_id: int):
    answer = await answer_repository.get_answer_by_id(answer_id)
    if not answer:
        return None

    total_votes = await vote_repository.total_votes_for_question(int(answer["question_id"]))
    if int(total_votes) > 0:
        return None 

    await answer_repository.delete_answer(answer_id)
    return True

