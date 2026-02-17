from fastapi import APIRouter, HTTPException, status

from model.vote_model import VoteCreate, VoteUpdate
from service import vote_service


router = APIRouter(tags=["votes"])


@router.post("/questions/{question_id}/vote", status_code=status.HTTP_201_CREATED)
async def create_vote(question_id: int, payload: VoteCreate):
    created, err = await vote_service.create_vote(
        question_id=question_id,
        user_id=payload.user_id,
        choice=payload.choice,
    )

    if err == "Question not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err == "User not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err == "User is not registered":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err)

    if err == "choice must be between 1 and 4":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)

    if err == "User already voted for this question":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err)

    if err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err)

    return created


@router.put("/questions/{question_id}/vote")
async def update_vote(question_id: int, payload: VoteUpdate):
    updated, err = await vote_service.update_vote(
        question_id=question_id,
        user_id=payload.user_id,
        choice=payload.choice,
    )

    if err == "Question not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err == "User not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err == "User is not registered":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err)

    if err == "choice must be between 1 and 4":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)

    if err == "Vote not found (use POST to create)":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err)

    return updated


@router.get("/questions/{question_id}/results")
async def get_results(question_id: int):
    result, err = await vote_service.results_for_question(question_id)

    if err == "Question not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    if err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err)

    return result
