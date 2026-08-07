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


class PracticeSessionResponse(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
    overall_feedback: Optional[str] = None
    behavioral_summary: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class PracticeQuestionRemarkResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    question_text: str
    rating: float
    feedback: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PracticeSessionSummaryResponse(BaseModel):
    session: PracticeSessionResponse
    remarks: List[PracticeQuestionRemarkResponse]
