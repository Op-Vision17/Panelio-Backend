import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class PracticeInterviewCreate(BaseModel):
    title: str
    job_description: Optional[str] = None
    difficulty: Optional[str] = "medium"
    duration: Optional[int] = 30


class PracticeInterviewResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    job_description: Optional[str] = None
    resume_filename: Optional[str] = None
    difficulty: str
    duration: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PracticeSessionListItemResponse(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    interview_title: Optional[str] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
    speech_score: Optional[float] = None
    video_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PracticeSessionResponse(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
    overall_feedback: Optional[str] = None
    overall_summary: Optional[str] = None
    speech_score: Optional[float] = None
    speech_summary: Optional[str] = None
    speech_metrics: Optional[dict] = None
    video_score: Optional[float] = None
    video_summary: Optional[str] = None
    video_metrics: Optional[dict] = None
    suggestions: Optional[List[str]] = None
    behavioral_summary: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class PracticeQuestionRemarkResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    question_text: str
    candidate_answer: Optional[str] = None
    what_was_missing: Optional[str] = None
    area_to_focus: Optional[str] = None
    score: Optional[float] = None
    rating: float
    feedback: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PracticeSessionSummaryResponse(BaseModel):
    session: PracticeSessionResponse
    remarks: List[PracticeQuestionRemarkResponse]

