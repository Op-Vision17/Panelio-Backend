import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.attend import handler
from app.features.attend.schema import (
    AnswerSubmitResponse,
    JoinVivaRequest,
    QuestionListResponse,
    SessionSummaryResponse,
    UserSessionResponse,
    VivaCodeDetailsResponse,
    VivaSessionResponse,
)
from app.shared.dependencies import get_current_user
from app.shared.responses import SuccessResponse, success_response

router = APIRouter()


@router.get("/code/{code}", response_model=SuccessResponse[VivaCodeDetailsResponse])
async def get_viva_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_get_viva_by_code(code, db, current_user)
    return success_response(data=res, message="Viva details retrieved successfully")


@router.post("/join", response_model=SuccessResponse[VivaSessionResponse])
async def join_viva(
    data: JoinVivaRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_join_viva(data, db, current_user)
    return success_response(data=res, message="Joined viva successfully")


@router.post(
    "/sessions/{session_id}/start", response_model=SuccessResponse[VivaSessionResponse]
)
async def start_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_start_session(session_id, db, current_user)
    return success_response(data=res, message="Viva session started successfully")


@router.get(
    "/sessions/{session_id}/questions",
    response_model=SuccessResponse[QuestionListResponse],
)
async def get_session_questions(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_get_session_questions(session_id, db, current_user)
    return success_response(data=res, message="Questions retrieved successfully")


@router.post(
    "/sessions/{session_id}/questions/{question_id}/answer",
    response_model=SuccessResponse[AnswerSubmitResponse],
)
async def submit_answer(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    res = await handler.handle_submit_answer(
        session_id=session_id,
        question_id=question_id,
        audio_file=audio_file,
        db=db,
        current_user=current_user,
        background_tasks=background_tasks,
    )
    return success_response(data=res, message="Answer submitted successfully")


@router.get(
    "/sessions/{session_id}/results",
    response_model=SuccessResponse[SessionSummaryResponse],
)
async def get_session_results(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_get_session_summary(session_id, db, current_user)
    return success_response(data=res, message="Session results retrieved successfully")


@router.get("/sessions", response_model=SuccessResponse[list[UserSessionResponse]])
async def get_user_sessions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_get_user_sessions(db, current_user)
    return success_response(data=res, message="Your joined vivas retrieved successfully")
