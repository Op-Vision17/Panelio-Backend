import base64
import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, UploadFile, WebSocket, status
from pypdf import PdfReader

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.features.practice import llm
from app.features.practice.behavioral import BehavioralAnalyzer, aggregate_session_behavior
from app.features.practice.dao import PracticeDAO
from app.features.practice.model import PracticeInterview, PracticeQuestionRemark, PracticeSession
from app.shared import audio

logger = logging.getLogger(__name__)

behavioral_analyzer = BehavioralAnalyzer()

UPLOAD_DIR = "uploads/practice"


def ensure_upload_dir_exists():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)


class ConnectionManager:
    """Manages active real-time WebSocket connections for sessions."""
    def __init__(self):
        self.active_connections: Dict[uuid.UUID, WebSocket] = {}

    async def connect(self, session_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: uuid.UUID):
        self.active_connections.pop(session_id, None)
        logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_json(self, session_id: uuid.UUID, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message on websocket for session {session_id}: {e}")


ws_manager = ConnectionManager()


async def extract_text_from_file(file: UploadFile) -> str:
    filename = file.filename.lower()
    content = await file.read()

    if filename.endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            extracted_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
            return extracted_text.strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF file: {str(e)}",
            )
    elif filename.endswith((".txt", ".md", ".json", ".csv")):
        try:
            return content.decode("utf-8").strip()
        except UnicodeDecodeError:
            try:
                return content.decode("latin-1").strip()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to decode text file: {str(e)}",
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a PDF or plain text file.",
        )


async def create_practice_interview(
    db,
    title: str,
    job_description: Optional[str],
    resume_file: Optional[UploadFile],
    user_id: uuid.UUID,
    difficulty: str = "medium",
    duration: int = 30
) -> PracticeInterview:
    resume_text = None
    resume_filename = None

    if resume_file and resume_file.filename:
        resume_filename = resume_file.filename
        resume_text = await extract_text_from_file(resume_file)

    dao = PracticeDAO(db)
    interview = PracticeInterview(
        user_id=user_id,
        title=title,
        job_description=job_description,
        resume_filename=resume_filename,
        resume_text=resume_text,
        difficulty=difficulty,
        duration=duration
    )
    return await dao.create_interview(interview)


async def get_practice_interviews(db, user_id: uuid.UUID) -> List[PracticeInterview]:
    dao = PracticeDAO(db)
    return list(await dao.get_interviews_by_user(user_id))


async def get_practice_interview(db, interview_id: uuid.UUID, user_id: uuid.UUID) -> PracticeInterview:
    dao = PracticeDAO(db)
    interview = await dao.get_interview_by_id(interview_id, user_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice interview configuration not found"
        )
    return interview


async def delete_practice_interview(db, interview_id: uuid.UUID, user_id: uuid.UUID):
    dao = PracticeDAO(db)
    deleted = await dao.delete_interview(interview_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice interview configuration not found"
        )


async def start_practice_session(db, interview_id: uuid.UUID, user_id: uuid.UUID) -> PracticeSession:
    # Verify interview ownership
    interview = await get_practice_interview(db, interview_id, user_id)

    dao = PracticeDAO(db)
    session = PracticeSession(
        interview_id=interview_id,
        user_id=user_id,
        status="started"
    )
    session = await dao.create_session(session)

    # Generate first question
    first_question = await llm.generate_first_question(
        job_description=interview.job_description,
        resume_text=interview.resume_text,
        difficulty=interview.difficulty
    )

    # Initial session state schema
    state = {
        "interview_id": str(interview_id),
        "user_id": str(user_id),
        "current_main_question": first_question,
        "dialogue_history": [
            {"role": "assistant", "content": first_question}
        ],
        "current_question_thread": [
            {"role": "assistant", "content": first_question}
        ],
        "followup_count": 0,
        "main_questions_asked": 1
    }

    # Save to Redis
    redis_client = await get_redis()
    await redis_client.set(f"practice:session:{session.id}", json.dumps(state))

    return session


async def get_session_summary(db, session_id: uuid.UUID, user_id: uuid.UUID) -> Dict:
    dao = PracticeDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    remarks = await dao.get_remarks_for_session(session_id)
    return {
        "session": session,
        "remarks": remarks
    }


async def submit_practice_audio_answer(
    db,
    session_id: uuid.UUID,
    audio_file: UploadFile,
    user_id: uuid.UUID
):
    """
    HTTP audio submission endpoint processing.
    """
    dao = PracticeDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found"
        )

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit answers for a completed interview session"
        )

    # Load state from Redis
    redis_client = await get_redis()
    state_json = await redis_client.get(f"practice:session:{session_id}")
    if not state_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session state not found in cache. Make sure WebSocket is connected."
        )
    state = json.loads(state_json)

    # Save audio temporarily
    ensure_upload_dir_exists()
    file_ext = os.path.splitext(audio_file.filename)[1] or ".wav"
    temp_filename = f"practice_{session_id}_{uuid.uuid4()}{file_ext}"
    filepath = os.path.join(UPLOAD_DIR, temp_filename)

    contents = await audio_file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    # Broadcast transcribing update
    await ws_manager.send_json(session_id, {"type": "status", "status": "transcribing"})

    # Transcribe audio using Groq Whisper
    try:
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        
        transcript = await audio.transcribe_audio(audio_bytes, temp_filename)
    except Exception as e:
        logger.error(f"Failed to transcribe practice answer: {e}")
        transcript = "[Audio transcription failed]"
    finally:
        # Clean up temp file
        if os.path.exists(filepath):
            os.remove(filepath)

    await ws_manager.send_json(session_id, {
        "type": "status",
        "status": "evaluating",
        "transcript": transcript
    })

    # Execute State Machine Loop
    await _execute_state_machine(db, session, state, transcript)


async def submit_practice_text_answer(
    db,
    session_id: uuid.UUID,
    answer_text: str,
    user_id: uuid.UUID
):
    """
    Helper for WebSocket directly calling text answer submissions.
    """
    dao = PracticeDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session or session.user_id != user_id:
        return

    redis_client = await get_redis()
    state_json = await redis_client.get(f"practice:session:{session_id}")
    if not state_json:
        return
    state = json.loads(state_json)

    await ws_manager.send_json(session_id, {"type": "status", "status": "evaluating"})
    await _execute_state_machine(db, session, state, answer_text)


async def record_behavioral_telemetry(session_id: uuid.UUID, telemetry_tick: dict):
    """
    Appends a behavioral telemetry tick (client pre-calculated or server CV output)
    to the Redis sliding session buffer.
    """
    try:
        redis_client = await get_redis()
        key = f"practice:session:{session_id}:behavior"
        await redis_client.rpush(key, json.dumps(telemetry_tick))
        await redis_client.ltrim(key, -1000, -1)
    except Exception as e:
        logger.error(f"Error recording behavioral telemetry tick: {e}")


async def process_and_record_behavioral_frame(session_id: uuid.UUID, base64_image: str):
    """
    Processes a raw base64 encoded image frame on the server, extracts CV landmarks/metrics,
    and appends result to Redis telemetry buffer.
    """
    try:
        if "," in base64_image:
            base64_image = base64_image.split(",", 1)[1]
        image_bytes = base64.b64decode(base64_image)
        tick = behavioral_analyzer.process_frame(image_bytes)
        await record_behavioral_telemetry(session_id, tick)
    except Exception as e:
        logger.error(f"Error processing base64 behavioral frame: {e}")


async def _execute_state_machine(db, session: PracticeSession, state: dict, user_answer: str):
    session_id = session.id
    redis_client = await get_redis()
    dao = PracticeDAO(db)

    # 1. Update active dialogue history
    state["dialogue_history"].append({"role": "user", "content": user_answer})
    state["current_question_thread"].append({"role": "user", "content": user_answer})

    # Fetch interview context
    interview = session.interview

    # 2. Run Deciding Node
    decision_data = await llm.evaluate_response_and_route(
        job_description=interview.job_description,
        resume_text=interview.resume_text,
        dialogue_history=state["dialogue_history"],
        latest_user_answer=user_answer,
        followup_count=state["followup_count"],
        difficulty=interview.difficulty
    )

    rating = decision_data.get("rating", 5.0)
    feedback = decision_data.get("feedback", "Recorded.")
    decision = decision_data.get("decision", "next_question")
    next_question_text = decision_data.get("next_question_text", "")

    # Broadcast answer evaluation results
    await ws_manager.send_json(session_id, {
        "type": "answer_graded",
        "rating": rating,
        "feedback": feedback
    })

    if decision == "followup" and state["followup_count"] < 2:
        # Pushing a followup
        state["followup_count"] += 1
        state["dialogue_history"].append({"role": "assistant", "content": next_question_text})
        state["current_question_thread"].append({"role": "assistant", "content": next_question_text})

        await redis_client.set(f"practice:session:{session_id}", json.dumps(state))
        await ws_manager.send_json(session_id, {
            "type": "new_question",
            "question_text": next_question_text,
            "is_followup": True
        })
        return

    # If decision is 'next_question' or 'end_interview' (or if we hit max followups):
    # 3. Generate and save consolidated remark for the current topic block
    consolidated_remark = await llm.generate_question_remark(
        main_question=state["current_main_question"],
        dialogue_thread=state["current_question_thread"]
    )

    remark_record = PracticeQuestionRemark(
        session_id=session_id,
        question_text=state["current_main_question"],
        rating=consolidated_remark.get("rating", rating),
        feedback=consolidated_remark.get("feedback", feedback)
    )
    await dao.create_question_remark(remark_record)

    # 4. Check ending conditions
    if decision == "end_interview" or state["main_questions_asked"] >= 5:
        # Wrap up session
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)

        # Retrieve and aggregate behavioral telemetry ticks from Redis
        raw_ticks_json = await redis_client.lrange(f"practice:session:{session_id}:behavior", 0, -1)
        raw_ticks = []
        for tick_str in raw_ticks_json:
            try:
                raw_ticks.append(json.loads(tick_str))
            except Exception:
                pass

        behavioral_summary = aggregate_session_behavior(raw_ticks)
        session.behavioral_summary = behavioral_summary

        # Calculate final aggregated scores and overall feedback via LLM
        remarks = await dao.get_remarks_for_session(session_id)
        if remarks:
            session.overall_score = round(sum(r.rating for r in remarks) / len(remarks), 2)
            session.overall_feedback = await llm.generate_overall_session_summary(
                interview_title=interview.title,
                remarks=[{"question_text": r.question_text, "rating": r.rating, "feedback": r.feedback} for r in remarks],
                behavioral_summary=behavioral_summary
            )
        else:
            session.overall_score = 0.0
            session.overall_feedback = "No questions completed."

        await dao.update_session(session)
        await redis_client.delete(f"practice:session:{session_id}")
        await redis_client.delete(f"practice:session:{session_id}:behavior")

        await ws_manager.send_json(session_id, {
            "type": "session_completed",
            "overall_score": session.overall_score,
            "overall_feedback": session.overall_feedback,
            "behavioral_summary": session.behavioral_summary
        })
    else:
        # Transition to next main question
        # If next_question_text is empty, generate it on the fly
        if not next_question_text:
            next_question_text = await llm.generate_first_question(
                job_description=interview.job_description,
                resume_text=interview.resume_text,
                difficulty=interview.difficulty
            )

        state["current_main_question"] = next_question_text
        state["dialogue_history"].append({"role": "assistant", "content": next_question_text})
        state["current_question_thread"] = [
            {"role": "assistant", "content": next_question_text}
        ]
        state["followup_count"] = 0
        state["main_questions_asked"] += 1

        await redis_client.set(f"practice:session:{session_id}", json.dumps(state))
        await ws_manager.send_json(session_id, {
            "type": "new_question",
            "question_text": next_question_text,
            "is_followup": False
        })
