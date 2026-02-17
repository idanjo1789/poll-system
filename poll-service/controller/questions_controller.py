from fastapi import APIRouter, HTTPException, Query, status

from model.question_model import QuestionCreate, QuestionUpdate
from service import question_service


router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_question(payload: QuestionCreate):
    return await question_service.create_question(
        title=payload.title,
        description=payload.description,
        is_active=payload.is_active,
    )


@router.get("")
async def list_questions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await question_service.list_questions(limit=limit, offset=offset)


@router.get("/{question_id}")
async def get_question(question_id: int):
    question = await question_service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


@router.put("/{question_id}")
async def update_question(question_id: int, payload: QuestionUpdate):
    updated = await question_service.update_question(
        question_id=question_id,
        title=payload.title,
        description=payload.description,
        is_active=payload.is_active,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return updated


@router.delete("/{question_id}")
async def delete_question(question_id: int):
    ok = await question_service.delete_question(question_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return {"deleted": True, "question_id": question_id}
