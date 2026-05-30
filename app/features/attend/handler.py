import uuid

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attend import service
from app.features.attend.schema import JoinVivaRequest


async def handle_get_viva_by_code(code: str, db: AsyncSession, current_user):
    return await service.get_viva_by_code(db, code, current_user.id)


async def handle_join_viva(data: JoinVivaRequest, db: AsyncSession, current_user):
    return await service.join_viva(db, data.code, current_user.id)


async def handle_start_session(session_id: uuid.UUID, db: AsyncSession, current_user):
    return await service.start_session(db, session_id, current_user.id)


async def handle_get_session_questions(
    session_id: uuid.UUID, db: AsyncSession, current_user
):
    return await service.get_session_questions(db, session_id, current_user.id)


async def handle_submit_answer(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    audio_file: UploadFile,
    db: AsyncSession,
    current_user,
    background_tasks: BackgroundTasks,
):
    return await service.submit_answer(
        db=db,
        session_id=session_id,
        question_id=question_id,
        audio_file=audio_file,
        user_id=current_user.id,
        background_tasks=background_tasks,
    )


async def handle_get_session_summary(
    session_id: uuid.UUID, db: AsyncSession, current_user
):
    return await service.get_session_summary(db, session_id, current_user.id)
