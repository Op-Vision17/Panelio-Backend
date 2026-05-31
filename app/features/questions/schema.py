import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class QuestionBase(BaseModel):
    question_text: str
    answer_text: str
    hint: Optional[str] = None


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    answer_text: Optional[str] = None
    hint: Optional[str] = None


class QuestionImproveRequest(BaseModel):
    instruction: str


class QuestionResponse(QuestionBase):
    id: uuid.UUID
    viva_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
