import uuid
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.features.practice.model import PracticeInterview, PracticeQuestionRemark, PracticeSession


class PracticeDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_interview(self, interview: PracticeInterview) -> PracticeInterview:
        self.db.add(interview)
        await self.db.commit()
        await self.db.refresh(interview)
        return interview

    async def get_interview_by_id(self, interview_id: uuid.UUID, user_id: uuid.UUID) -> PracticeInterview | None:
        stmt = select(PracticeInterview).where(
            PracticeInterview.id == interview_id,
            PracticeInterview.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_interviews_by_user(self, user_id: uuid.UUID) -> Sequence[PracticeInterview]:
        stmt = (
            select(PracticeInterview)
            .where(PracticeInterview.user_id == user_id)
            .order_by(PracticeInterview.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_interview(self, interview_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        interview = await self.get_interview_by_id(interview_id, user_id)
        if interview:
            await self.db.delete(interview)
            await self.db.commit()
            return True
        return False

    async def create_session(self, session: PracticeSession) -> PracticeSession:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session_by_id(self, session_id: uuid.UUID) -> PracticeSession | None:
        stmt = (
            select(PracticeSession)
            .options(
                selectinload(PracticeSession.interview),
                selectinload(PracticeSession.user),
            )
            .where(PracticeSession.id == session_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_session(self, session: PracticeSession) -> PracticeSession:
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_sessions_by_user(self, user_id: uuid.UUID) -> Sequence[PracticeSession]:
        stmt = (
            select(PracticeSession)
            .options(selectinload(PracticeSession.interview))
            .where(PracticeSession.user_id == user_id)
            .order_by(PracticeSession.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_sessions_for_interview(self, interview_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[PracticeSession]:
        stmt = (
            select(PracticeSession)
            .where(
                PracticeSession.interview_id == interview_id,
                PracticeSession.user_id == user_id
            )
            .order_by(PracticeSession.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        session = await self.get_session_by_id(session_id)
        if session and session.user_id == user_id:
            await self.db.delete(session)
            await self.db.commit()
            return True
        return False

    async def create_question_remark(self, remark: PracticeQuestionRemark) -> PracticeQuestionRemark:
        self.db.add(remark)
        await self.db.commit()
        await self.db.refresh(remark)
        return remark

    async def get_remarks_for_session(self, session_id: uuid.UUID) -> Sequence[PracticeQuestionRemark]:
        stmt = (
            select(PracticeQuestionRemark)
            .where(PracticeQuestionRemark.session_id == session_id)
            .order_by(PracticeQuestionRemark.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

