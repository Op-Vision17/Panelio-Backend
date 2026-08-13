import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PracticeInterview(Base):
    __tablename__ = "practice_interviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_docs_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User")
    sessions: Mapped[list["PracticeSession"]] = relationship(
        "PracticeSession", back_populates="interview", cascade="all, delete-orphan"
    )


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("practice_interviews.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, default="started", nullable=False
    )  # started, completed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    speech_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    video_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    video_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    behavioral_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    interview: Mapped["PracticeInterview"] = relationship("PracticeInterview", back_populates="sessions")
    user: Mapped["User"] = relationship("User")
    remarks: Mapped[list["PracticeQuestionRemark"]] = relationship(
        "PracticeQuestionRemark", back_populates="session", cascade="all, delete-orphan"
    )


class PracticeQuestionRemark(Base):
    __tablename__ = "practice_question_remarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_was_missing: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_to_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feedback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped["PracticeSession"] = relationship("PracticeSession", back_populates="remarks")

