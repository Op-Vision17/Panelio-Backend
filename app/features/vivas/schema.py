import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class QuestionResponse(BaseModel):
    id: uuid.UUID
    viva_id: uuid.UUID
    question_text: str
    answer_text: str
    hint: Optional[str] = None
    order_index: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionCreate(BaseModel):
    question_text: str
    answer_text: str
    hint: Optional[str] = None


class QuestionsGenerateRequest(BaseModel):
    topic: str
    num_questions: int = 5
    doc_text: Optional[str] = None


class QuestionsGenerateTopicRequest(BaseModel):
    topic: str
    num_questions: int = 5


class VivaCreate(BaseModel):
    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = 15


class VivaUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None


class VivaResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    created_at: datetime
    owner_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class VivaDetailResponse(VivaResponse):
    questions: List[QuestionResponse] = []
