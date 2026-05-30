import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import HTTPException, UploadFile, status

from app.core.database import AsyncSessionLocal
from app.features.attend.dao import AttendDAO
from app.features.attend.model import AttendeeAnswer, VivaSession
from app.features.attend.schema import (
    AnswerSubmitResponse,
    QuestionItem,
    QuestionListResponse,
    SessionAnswerSummary,
    SessionSummaryResponse,
    VivaCodeDetailsResponse,
    VivaSessionResponse,
)
from app.features.questions.model import Question
from app.features.vivas.model import Viva
from app.shared import audio, llm

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads/audio"


def ensure_upload_dir_exists():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)


async def check_and_enforce_session_expiration(db, session: VivaSession) -> bool:
    """
    Check if the session has expired. If yes, transition status to 'completed',
    calculate overall score (unanswered questions count as 0), and return True.
    """
    if session.status == "completed":
        return True

    if session.status == "started" and session.expires_at:
        utc_now = datetime.now(timezone.utc)
        viva = session.viva

        is_expired = utc_now > session.expires_at
        if viva.end_time and utc_now > viva.end_time:
            is_expired = True

        if is_expired:
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)

            dao = AttendDAO(db)
            answers = await dao.get_answers_for_session(session.id)
            questions = await dao.get_questions_by_viva(session.viva_id)

            if questions:
                # Sum of ratings of answers (graded ones), treating missing/ungraded as 0
                total_score = sum(a.rating for a in answers if a.rating is not None)
                session.overall_score = round(total_score / len(questions), 2)
            else:
                session.overall_score = 0.0

            await dao.update_session(session)
            return True

    return False


async def get_viva_by_code(
    db, code: str, user_id: uuid.UUID
) -> VivaCodeDetailsResponse:
    dao = AttendDAO(db)
    viva = await dao.get_viva_by_code(code)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viva not found with this code",
        )

    # Check if a session already exists for this user
    session = await dao.get_session_by_user_and_viva(user_id, viva.id)

    return VivaCodeDetailsResponse(
        viva_id=viva.id,
        name=viva.name,
        start_time=viva.start_time,
        end_time=viva.end_time,
        duration=viva.duration,
        is_joined=session is not None,
        session_id=session.id if session else None,
    )


async def join_viva(db, code: str, user_id: uuid.UUID) -> VivaSessionResponse:
    dao = AttendDAO(db)
    viva = await dao.get_viva_by_code(code)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viva not found with this code",
        )

    # Check if session exists
    session = await dao.get_session_by_user_and_viva(user_id, viva.id)
    if session:
        return VivaSessionResponse.model_validate(session)

    # Check if overall viva has already ended
    utc_now = datetime.now(timezone.utc)
    if viva.end_time and utc_now > viva.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join because this viva has already ended",
        )

    new_session = VivaSession(
        viva_id=viva.id,
        user_id=user_id,
        status="joined",
    )
    session = await dao.create_session(new_session)
    return VivaSessionResponse.model_validate(session)


async def start_session(
    db, session_id: uuid.UUID, user_id: uuid.UUID
) -> VivaSessionResponse:
    dao = AttendDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva session not found"
        )

    # Update expiration status if needed
    await check_and_enforce_session_expiration(db, session)

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start a completed session",
        )
    elif session.status == "started":
        return VivaSessionResponse.model_validate(session)

    # Validate overall start time and end time
    viva = session.viva
    utc_now = datetime.now(timezone.utc)

    if viva.start_time and utc_now < viva.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Viva has not started yet"
        )
    if viva.end_time and utc_now > viva.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Viva has ended"
        )

    session.status = "started"
    session = await dao.update_session(session)
    return VivaSessionResponse.model_validate(session)


async def get_session_questions(
    db, session_id: uuid.UUID, user_id: uuid.UUID
) -> QuestionListResponse:
    dao = AttendDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva session not found"
        )

    # Update expiration status if needed
    is_expired = await check_and_enforce_session_expiration(db, session)

    if session.status == "joined":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please start the session first",
        )
    elif session.status == "completed" or is_expired:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This session has ended"
        )

    # If first time fetching questions, start the timer
    if session.started_at is None:
        utc_now = datetime.now(timezone.utc)
        duration_mins = session.viva.duration or 15

        session.started_at = utc_now
        session.expires_at = utc_now + timedelta(minutes=duration_mins)
        session = await dao.update_session(session)

    # Fetch questions and answers
    questions = await dao.get_questions_by_viva(session.viva_id)
    answers = await dao.get_answers_for_session(session.id)
    submitted_question_ids = {a.question_id for a in answers}

    items = []
    for q in questions:
        items.append(
            QuestionItem(
                question_id=q.id,
                question_text=q.question_text,
                hint=q.hint,
                is_submitted=q.id in submitted_question_ids,
            )
        )

    return QuestionListResponse(expires_at=session.expires_at, questions=items)


async def submit_answer(
    db,
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    audio_file: UploadFile,
    user_id: uuid.UUID,
    background_tasks,
) -> AnswerSubmitResponse:
    dao = AttendDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva session not found"
        )

    # Check expiration
    is_expired = await check_and_enforce_session_expiration(db, session)
    if session.status == "completed" or is_expired:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This session is no longer active",
        )
    if session.status == "joined" or session.started_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Questions have not been revealed yet",
        )

    # Verify question belongs to the viva
    questions = await dao.get_questions_by_viva(session.viva_id)
    question = next((q for q in questions if q.id == question_id), None)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found in this viva",
        )

    # Check if already answered
    existing_answer = await dao.get_answer(session_id, question_id)
    if existing_answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted an answer for this question",
        )

    # Save audio temporarily
    ensure_upload_dir_exists()
    file_ext = os.path.splitext(audio_file.filename)[1] or ".wav"
    temp_filename = f"{session_id}_{question_id}{file_ext}"
    filepath = os.path.join(UPLOAD_DIR, temp_filename)

    contents = await audio_file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    # Create placeholder answer to lock the submission
    new_answer = AttendeeAnswer(
        session_id=session_id,
        question_id=question_id,
        audio_url=filepath,
        transcript=None,
        rating=None,
        feedback=None,
    )
    await dao.create_answer(new_answer)

    # Queue background task for speech-to-text transcription and grading
    background_tasks.add_task(
        process_audio_in_background, session_id, question_id, filepath
    )

    return AnswerSubmitResponse(
        session_id=session_id,
        question_id=question_id,
        status="submitted",
    )


async def process_audio_in_background(
    session_id: uuid.UUID, question_id: uuid.UUID, filepath: str
):
    """
    Asynchronous background execution to transcribe the audio, evaluate it, and update status.
    """
    logger.info(
        f"Background processing started for session {session_id}, question {question_id}"
    )

    # Read audio bytes
    audio_bytes = b""
    try:
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                audio_bytes = f.read()
    except Exception as e:
        logger.error(f"Failed to read temporary audio file {filepath}: {e}")

    # Transcribe audio using Groq Whisper
    transcript = ""
    transcription_error = False
    if audio_bytes:
        try:
            transcript = await audio.transcribe_audio(
                audio_bytes, os.path.basename(filepath)
            )
        except Exception as e:
            logger.error(f"Groq Whisper transcription failed: {e}")
            transcription_error = True

    # Delete audio file immediately
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted temporary audio file {filepath}")
    except Exception as e:
        logger.error(f"Failed to delete temporary audio file {filepath}: {e}")

    # Evaluate the transcription using Groq LLM
    rating = 0.0
    feedback = ""

    async with AsyncSessionLocal() as db:
        dao = AttendDAO(db)

        # Reload objects in this DB context
        session = await dao.get_session_by_id(session_id)
        if not session:
            logger.error(f"Session {session_id} not found in background task")
            return

        questions = await dao.get_questions_by_viva(session.viva_id)
        question = next((q for q in questions if q.id == question_id), None)

        if not question:
            logger.error(
                f"Question {question_id} not found for session {session_id} in background task"
            )
            return

        answer_record = await dao.get_answer(session_id, question_id)
        if not answer_record:
            logger.error(
                f"Answer record not found in database for session {session_id}, question {question_id}"
            )
            return

        if transcription_error:
            rating = 0.0
            feedback = "Evaluation skipped because audio transcription failed due to an internal API error."
        elif not transcript or len(transcript.strip()) == 0:
            rating = 0.0
            feedback = "No speech detected. Please ensure your microphone is working and you answered the question."
        else:
            try:
                eval_res = await llm.evaluate_answer(
                    question_text=question.question_text,
                    correct_answer=question.answer_text,
                    user_answer=transcript,
                )
                rating = eval_res.get("rating", 0.0)
                feedback = eval_res.get("feedback", "No feedback provided.")
            except Exception as e:
                logger.error(f"Groq answer evaluation failed: {e}")
                rating = 0.0
                feedback = "Failed to evaluate response due to an internal LLM error."

        # Save results
        answer_record.transcript = transcript or ""
        answer_record.rating = rating
        answer_record.feedback = feedback
        await dao.update_answer(answer_record)

        # Check if all questions have been answered and processed
        answers = await dao.get_answers_for_session(session_id)

        # A session is completed if all questions of the viva have answers AND all answers have been rated (not null)
        all_questions_answered = len(answers) == len(questions)
        all_evaluations_done = all(a.rating is not None for a in answers)

        if all_questions_answered and all_evaluations_done:
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            total_rating = sum(a.rating for a in answers)
            session.overall_score = round(total_rating / len(questions), 2)
            await dao.update_session(session)
            logger.info(
                f"Session {session_id} marked as COMPLETED. Score: {session.overall_score}"
            )


async def get_session_summary(
    db, session_id: uuid.UUID, user_id: uuid.UUID
) -> SessionSummaryResponse:
    dao = AttendDAO(db)
    session = await dao.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva session not found"
        )

    # Authorization check: either the attendee themselves, or the viva creator/owner can view the summary
    is_authorized = (session.user_id == user_id) or (session.viva.owner_id == user_id)
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this summary",
        )

    # Force expiration check to close active timers if the user accesses results after expiration
    await check_and_enforce_session_expiration(db, session)

    answers = await dao.get_answers_for_session(session_id)
    questions = await dao.get_questions_by_viva(session.viva_id)

    # Build answer details map
    answer_map = {a.question_id: a for a in answers}

    summaries = []
    for q in questions:
        ans = answer_map.get(q.id)
        summaries.append(
            SessionAnswerSummary(
                question_text=q.question_text,
                expected_answer=q.answer_text,
                transcript=ans.transcript if ans else None,
                rating=ans.rating if ans else None,
                feedback=ans.feedback if ans else None,
                answered_at=ans.answered_at if ans else datetime.now(timezone.utc),
            )
        )

    return SessionSummaryResponse(
        session_id=session.id,
        viva_name=session.viva.name,
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        overall_score=session.overall_score,
        answers=summaries,
    )
