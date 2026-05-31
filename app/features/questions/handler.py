import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.questions import service
from app.features.questions.schema import (
    QuestionImproveRequest,
    QuestionUpdate,
)


async def handle_update_question(
    question_id: uuid.UUID, data: QuestionUpdate, db: AsyncSession, current_user
):
    return await service.update_question(db, question_id, current_user.id, data)


async def handle_delete_question(
    question_id: uuid.UUID, db: AsyncSession, current_user
):
    await service.delete_question(db, question_id, current_user.id)



async def handle_improve_question(
    question_id: uuid.UUID, data: QuestionImproveRequest, db: AsyncSession, current_user
):
    return await service.improve_existing_question(
        db, question_id, current_user.id, data
    )
