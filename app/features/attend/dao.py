import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.features.attend.model import AttendeeAnswer, VivaSession
from app.features.questions.model import Question
from app.features.vivas.model import Viva


class AttendDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_session_by_id(self, session_id: uuid.UUID) -> VivaSession | None:
        stmt = (
            select(VivaSession)
            .options(
                selectinload(VivaSession.viva),
                selectinload(VivaSession.user),
            )
            .where(VivaSession.id == session_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_session_by_user_and_viva(
        self, user_id: uuid.UUID, viva_id: uuid.UUID
    ) -> VivaSession | None:
        stmt = select(VivaSession).where(
            VivaSession.user_id == user_id, VivaSession.viva_id == viva_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_session(self, session: VivaSession) -> VivaSession:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def update_session(self, session: VivaSession) -> VivaSession:
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_viva_by_code(self, code: str) -> Viva | None:
        stmt = select(Viva).where(Viva.code == code)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_answer(
        self, session_id: uuid.UUID, question_id: uuid.UUID
    ) -> AttendeeAnswer | None:
        stmt = select(AttendeeAnswer).where(
            AttendeeAnswer.session_id == session_id,
            AttendeeAnswer.question_id == question_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_answer(self, answer: AttendeeAnswer) -> AttendeeAnswer:
        self.db.add(answer)
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    async def update_answer(self, answer: AttendeeAnswer) -> AttendeeAnswer:
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    async def get_answers_for_session(
        self, session_id: uuid.UUID
    ) -> list[AttendeeAnswer]:
        stmt = (
            select(AttendeeAnswer)
            .options(selectinload(AttendeeAnswer.question))
            .where(AttendeeAnswer.session_id == session_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_questions_by_viva(self, viva_id: uuid.UUID) -> list[Question]:
        stmt = (
            select(Question)
            .where(Question.viva_id == viva_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_sessions_by_viva(self, viva_id: uuid.UUID) -> list[VivaSession]:
        stmt = (
            select(VivaSession)
            .options(selectinload(VivaSession.user))
            .where(VivaSession.viva_id == viva_id)
            .order_by(VivaSession.joined_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_sessions_by_user(self, user_id: uuid.UUID) -> list[VivaSession]:
        stmt = (
            select(VivaSession)
            .options(selectinload(VivaSession.viva))
            .where(VivaSession.user_id == user_id)
            .order_by(VivaSession.joined_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
