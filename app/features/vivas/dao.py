import uuid

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.features.questions.model import Question
from app.features.vivas.model import Viva


class VivaDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id_and_owner(
        self, viva_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Viva | None:
        stmt = select(Viva).where(Viva.id == viva_id, Viva.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id_with_questions(
        self, viva_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Viva | None:
        stmt = (
            select(Viva)
            .options(selectinload(Viva.questions))
            .where(Viva.id == viva_id, Viva.owner_id == owner_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Viva | None:
        stmt = select(Viva).where(Viva.code == code)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Viva]:
        stmt = (
            select(Viva)
            .where(Viva.owner_id == owner_id)
            .order_by(Viva.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, viva: Viva) -> Viva:
        self.db.add(viva)
        await self.db.commit()
        await self.db.refresh(viva)
        return viva

    async def update(self, viva: Viva) -> Viva:
        await self.db.commit()
        await self.db.refresh(viva)
        return viva

    async def delete(self, viva: Viva) -> None:
        await self.db.delete(viva)
        await self.db.commit()

    async def get_viva_by_id_raw(self, viva_id: uuid.UUID) -> Viva | None:
        return await self.db.get(Viva, viva_id)

    async def create_question(self, question: Question) -> Question:
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def get_questions_by_viva_id(self, viva_id: uuid.UUID) -> list[Question]:
        stmt = (
            select(Question)
            .where(Question.viva_id == viva_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_questions(self, questions: list[Question]) -> list[Question]:
        self.db.add_all(questions)
        await self.db.commit()
        for q in questions:
            await self.db.refresh(q)
        return questions
