from repository import vote_repository
from repository import question_repository
from service import user_service_api
from repository import answer_repository


def _validate_choice(choice: int) -> bool:
    return 1 <= int(choice) <= 4


async def _ensure_registered_user(user_id: int):
    user = await user_service_api.get_user(user_id)
    if not user:
        return None, "User not found"

    if not bool(user.get("is_registered", False)):
        return None, "User is not registered"

    return user, None


async def create_vote(question_id: int, user_id: int, choice: int):

    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None, "Question not found"


    _, err = await _ensure_registered_user(user_id)
    if err:
        return None, err


    if not _validate_choice(choice):
        return None, "choice must be between 1 and 4"


    existing = await vote_repository.get_user_vote_for_question(user_id=user_id, question_id=question_id)
    if existing:
        return None, "User already voted for this question"

    created = await vote_repository.create_vote(question_id=question_id, user_id=user_id, choice=int(choice))
    if not created:
        return None, "Failed to create vote"

    return created, None


async def update_vote(question_id: int, user_id: int, choice: int):

    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None, "Question not found"


    _, err = await _ensure_registered_user(user_id)
    if err:
        return None, err


    if not _validate_choice(choice):
        return None, "choice must be between 1 and 4"


    existing = await vote_repository.get_user_vote_for_question(user_id=user_id, question_id=question_id)
    if not existing:
        return None, "Vote not found (use POST to create)"


    if int(existing["choice"]) == int(choice):
        return existing, None

    updated = await vote_repository.update_vote_choice(vote_id=int(existing["vote_id"]), choice=int(choice))
    if not updated:
        return None, "Vote not found"

    return updated, None


async def results_for_question(question_id: int):

    question = await question_repository.get_question_by_id(question_id)
    if not question:
        return None, "Question not found"

    results = await vote_repository.results_for_question(question_id)
    total = await vote_repository.total_votes_for_question(question_id)

    return {
        "question_id": int(question_id),
        "total_votes": int(total),
        "results": results,
    }, None

