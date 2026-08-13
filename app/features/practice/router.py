import json
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import verify_token
from app.features.practice import service
from app.features.practice.schema import (
    PracticeInterviewResponse,
    PracticeSessionListItemResponse,
    PracticeSessionResponse,
    PracticeSessionSummaryResponse,
)
from app.features.practice.service import ws_manager
from app.shared.dependencies import get_current_onboarded_user
from app.shared.responses import SuccessResponse, success_response

logger = logging.getLogger(__name__)

router = APIRouter()



@router.post("/interviews", response_model=SuccessResponse[PracticeInterviewResponse], status_code=status.HTTP_201_CREATED)
async def create_interview(
    title: str = Form(...),
    job_description: Optional[str] = Form(None),
    resume_file: Optional[UploadFile] = File(None),
    difficulty: str = Form("medium"),
    duration: int = Form(30),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    res = await service.create_practice_interview(
        db=db,
        title=title,
        job_description=job_description,
        resume_file=resume_file,
        user_id=current_user.id,
        difficulty=difficulty,
        duration=duration
    )
    return success_response(
        data=PracticeInterviewResponse.model_validate(res),
        message="Practice interview created successfully"
    )


@router.get("/interviews", response_model=SuccessResponse[List[PracticeInterviewResponse]])
async def get_interviews(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    res = await service.get_practice_interviews(db, current_user.id)
    return success_response(
        data=[PracticeInterviewResponse.model_validate(x) for x in res],
        message="Practice interviews retrieved successfully"
    )


@router.get("/interviews/{interview_id}", response_model=SuccessResponse[PracticeInterviewResponse])
async def get_interview(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    res = await service.get_practice_interview(db, interview_id, current_user.id)
    return success_response(
        data=PracticeInterviewResponse.model_validate(res),
        message="Practice interview retrieved successfully"
    )


@router.delete("/interviews/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    await service.delete_practice_interview(db, interview_id, current_user.id)


@router.post("/interviews/{interview_id}/sessions", response_model=SuccessResponse[PracticeSessionResponse])
async def start_session(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    res = await service.start_practice_session(db, interview_id, current_user.id)
    return success_response(
        data=PracticeSessionResponse.model_validate(res),
        message="Practice interview session started successfully"
    )


@router.post("/sessions/{session_id}/answer", response_model=SuccessResponse[dict])
async def submit_audio_answer(
    session_id: uuid.UUID,
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    await service.submit_practice_audio_answer(
        db=db,
        session_id=session_id,
        audio_file=audio_file,
        user_id=current_user.id
    )
    return success_response(
        data={"status": "processing"},
        message="Answer received. Processing and evaluating..."
    )


@router.get("/sessions", response_model=SuccessResponse[List[PracticeSessionListItemResponse]])
async def get_user_sessions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    res = await service.get_user_practice_sessions(db, current_user.id)
    return success_response(
        data=[PracticeSessionListItemResponse.model_validate(x) for x in res],
        message="User practice sessions retrieved successfully"
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    await service.delete_practice_session(db, session_id, current_user.id)


@router.get("/sessions/{session_id}/summary", response_model=SuccessResponse[PracticeSessionSummaryResponse])
async def get_session_summary(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_onboarded_user)
):
    res = await service.get_session_summary(db, session_id, current_user.id)
    return success_response(
        data=PracticeSessionSummaryResponse.model_validate(res),
        message="Practice session summary retrieved successfully"
    )



@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token query parameter required")
        return

    try:
        payload = verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Invalid subject key")
        user_id = uuid.UUID(user_id_str)
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    # Check session ownership
    from app.features.practice.dao import PracticeDAO
    dao = PracticeDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session or session.user_id != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session not found or access denied")
        return

    await ws_manager.connect(session_id, websocket)

    try:
        # Load and send the latest question state upon connecting
        redis_client = await get_redis()
        state_json = await redis_client.get(f"practice:session:{session_id}")
        if state_json:
            state = json.loads(state_json)
            is_followup = state.get("followup_count", 0) > 0
            await websocket.send_json({
                "type": "new_question",
                "question_text": state.get("current_main_question"),
                "is_followup": is_followup
            })

        while True:
            # Handle text-only answer submissions & real-time behavioral telemetry via WS
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "submit_answer":
                text_ans = data.get("text")
                if text_ans:
                    await service.submit_practice_text_answer(
                        db=db,
                        session_id=session_id,
                        answer_text=text_ans,
                        user_id=user_id
                    )
            elif msg_type == "behavioral_tick":
                tick_data = data.get("data") if isinstance(data.get("data"), dict) else data
                await service.record_behavioral_telemetry(session_id, tick_data)
            elif msg_type == "behavioral_frame":
                base64_img = data.get("image")
                if base64_img:
                    await service.process_and_record_behavioral_frame(session_id, base64_img)
    except Exception as e:
        logger.info(f"WebSocket session {session_id} disconnected or closed: {e}")
    finally:
        ws_manager.disconnect(session_id)
