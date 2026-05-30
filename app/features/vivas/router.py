import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.vivas import handler
from app.features.vivas.schema import (
    QuestionCreate,
    QuestionResponse,
    QuestionsGenerateRequest,
    QuestionsGenerateTopicRequest,
    VivaCreate,
    VivaDetailResponse,
    VivaResponse,
    VivaUpdate,
)
from app.shared.dependencies import get_current_user
from app.shared.responses import SuccessResponse, success_response

router = APIRouter()


@router.post(
    "",
    response_model=SuccessResponse[VivaResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_viva(
    data: VivaCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_create_viva(data, db, current_user)
    return success_response(data=res, message="Viva created successfully")


@router.get("", response_model=SuccessResponse[List[VivaResponse]])
async def get_vivas(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    res = await handler.handle_get_vivas(db, current_user)
    return success_response(data=res, message="Vivas retrieved successfully")


@router.get("/{viva_id}", response_model=SuccessResponse[VivaDetailResponse])
async def get_viva(
    viva_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_get_viva(viva_id, db, current_user)
    return success_response(data=res, message="Viva retrieved successfully")


@router.patch("/{viva_id}", response_model=SuccessResponse[VivaResponse])
async def update_viva(
    viva_id: uuid.UUID,
    data: VivaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_update_viva(viva_id, data, db, current_user)
    return success_response(data=res, message="Viva updated successfully")


@router.delete("/{viva_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_viva(
    viva_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_delete_viva(viva_id, db, current_user)


@router.post(
    "/{viva_id}/questions",
    response_model=SuccessResponse[QuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_viva_question(
    viva_id: uuid.UUID,
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_create_viva_question(viva_id, data, db, current_user)
    return success_response(data=res, message="Question created successfully")


@router.get(
    "/{viva_id}/questions",
    response_model=SuccessResponse[List[QuestionResponse]],
)
async def get_viva_questions(
    viva_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_get_viva_questions(viva_id, db, current_user)
    return success_response(data=res, message="Questions retrieved successfully")


@router.post(
    "/{viva_id}/questions/generate/topic",
    response_model=SuccessResponse[List[QuestionResponse]],
    status_code=status.HTTP_201_CREATED,
)
async def generate_viva_questions_topic(
    viva_id: uuid.UUID,
    data: QuestionsGenerateTopicRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_generate_viva_questions_from_topic(
        viva_id, data, db, current_user
    )
    return success_response(data=res, message="Questions generated from topic successfully")


@router.post(
    "/{viva_id}/questions/generate/document",
    response_model=SuccessResponse[List[QuestionResponse]],
    status_code=status.HTTP_201_CREATED,
)
async def generate_viva_questions_document(
    viva_id: uuid.UUID,
    num_questions: int = Form(5),
    doc_text: Optional[str] = Form(None),
    doc_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_generate_viva_questions_from_document(
        viva_id=viva_id,
        num_questions=num_questions,
        doc_text=doc_text,
        doc_file=doc_file,
        db=db,
        current_user=current_user,
    )
    return success_response(data=res, message="Questions generated from document successfully")
