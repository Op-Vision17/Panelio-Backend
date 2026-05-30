import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VivaSession(Base):
    __tablename__ = "viva_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    viva_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vivas.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, default="joined", nullable=False
    )  # joined, started, completed
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)

    viva: Mapped["Viva"] = relationship("Viva")
    user: Mapped["User"] = relationship("User")
    answers: Mapped[list["AttendeeAnswer"]] = relationship(
        "AttendeeAnswer", back_populates="session", cascade="all, delete-orphan"
    )


class AttendeeAnswer(Base):
    __tablename__ = "attendee_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("viva_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    audio_url: Mapped[str] = mapped_column(String, nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session: Mapped["VivaSession"] = relationship(
        "VivaSession", back_populates="answers"
    )
    question: Mapped["Question"] = relationship("Question")

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_session_question"),
    )
