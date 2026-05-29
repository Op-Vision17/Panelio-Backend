import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.questions import handler
from app.features.questions.schema import (
    QuestionBase,
    QuestionImproveRequest,
    QuestionResponse,
    QuestionUpdate,
    ReorderRequest,
)
from app.shared.dependencies import get_current_user

router = APIRouter()


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: uuid.UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_update_question(question_id, data, db, current_user)


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question_put(
    question_id: uuid.UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_update_question(question_id, data, db, current_user)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_delete_question(question_id, db, current_user)


@router.post("/reorder", status_code=status.HTTP_200_OK)
async def reorder_questions(
    data: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await handler.handle_reorder_questions(data, db, current_user)
    return {"detail": "Questions reordered successfully"}


@router.post("/{question_id}/improve", response_model=QuestionBase)
async def improve_question(
    question_id: uuid.UUID,
    data: QuestionImproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_improve_question(question_id, data, db, current_user)
