import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class VivaCodeDetailsResponse(BaseModel):
    viva_id: uuid.UUID
    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    is_joined: bool
    session_id: Optional[uuid.UUID] = None


class JoinVivaRequest(BaseModel):
    code: str


class VivaSessionResponse(BaseModel):
    id: uuid.UUID = Field(serialization_alias="session_id")
    viva_id: uuid.UUID
    status: str
    joined_at: datetime
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class QuestionItem(BaseModel):
    question_id: uuid.UUID
    question_text: str
    hint: Optional[str] = None
    is_submitted: bool


class QuestionListResponse(BaseModel):
    expires_at: Optional[datetime] = None
    questions: List[QuestionItem]


class AnswerSubmitResponse(BaseModel):
    session_id: uuid.UUID
    question_id: uuid.UUID
    status: str


class SessionAnswerSummary(BaseModel):
    question_text: str
    expected_answer: str
    transcript: Optional[str] = None
    rating: Optional[float] = None
    feedback: Optional[str] = None
    answered_at: datetime


class SessionSummaryResponse(BaseModel):
    session_id: uuid.UUID
    viva_name: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
    answers: List[SessionAnswerSummary]


class VivaAttendeeSessionResponse(BaseModel):
    session_id: uuid.UUID
    attendee_email: str
    status: str
    overall_score: Optional[float] = None
    completed_at: Optional[datetime] = None


class UserSessionResponse(BaseModel):
    session_id: uuid.UUID
    viva_id: uuid.UUID
    viva_name: str
    viva_code: str
    viva_start_time: Optional[datetime] = None
    viva_end_time: Optional[datetime] = None
    status: str
    joined_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
