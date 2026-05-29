import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.features.questions.model import Question


class QuestionDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id_with_viva(self, question_id: uuid.UUID) -> Question | None:
        query = (
            select(Question)
            .options(joinedload(Question.viva))
            .where(Question.id == question_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_ids_with_viva(
        self, question_ids: list[uuid.UUID]
    ) -> list[Question]:
        query = (
            select(Question)
            .options(joinedload(Question.viva))
            .where(Question.id.in_(question_ids))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, question: Question) -> Question:
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def delete(self, question: Question) -> None:
        await self.db.delete(question)
        await self.db.commit()

    async def save_changes(self) -> None:
        await self.db.commit()
