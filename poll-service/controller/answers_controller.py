from fastapi import APIRouter, HTTPException, Query, status

from model.answer_model import AnswerCreate
from service import answer_service


router = APIRouter(tags=["answers"])


@router.post("/questions/{question_id}/answers", status_code=status.HTTP_201_CREATED)
async def create_answer(question_id: int, payload: AnswerCreate):
    created, err = await answer_service.create_answer_for_question(
        question_id=question_id,
        text_value=payload.text,
    )

    if err == "Question not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err == "Answer text is required":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)

    if err == "Question already has 4 answers":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err)

    if err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err)

    return created


@router.get("/questions/{question_id}/answers")
async def list_answers(
    question_id: int,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    result, err = await answer_service.list_answers_for_question(
        question_id=question_id,
        limit=limit,
        offset=offset,
    )

    if err == "Question not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err)

    return result


@router.delete("/answers/{answer_id}")
async def delete_answer(answer_id: int):
    ok = await answer_service.delete_answer(answer_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
    return {"deleted": True, "answer_id": answer_id}
