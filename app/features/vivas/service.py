import random
import string

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.features.vivas.model import Viva
from app.features.vivas.schema import VivaCreate, VivaUpdate


async def generate_viva_code(db: AsyncSession) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=6))
        stmt = select(Viva).where(Viva.code == code)
        result = await db.execute(stmt)
        if not result.scalars().first():
            return code


async def create_viva(db: AsyncSession, data: VivaCreate, user_id) -> Viva:
    code = await generate_viva_code(db)
    viva = Viva(
        owner_id=user_id,
        name=data.name,
        code=code,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(viva)
    await db.commit()
    await db.refresh(viva)
    return viva


async def get_vivas(db: AsyncSession, user_id) -> list[Viva]:
    stmt = select(Viva).where(Viva.owner_id == user_id).order_by(Viva.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_viva_by_id(db: AsyncSession, viva_id, user_id) -> Viva:
    stmt = (
        select(Viva)
        .options(selectinload(Viva.questions))
        .where(Viva.id == viva_id, Viva.owner_id == user_id)
    )
    result = await db.execute(stmt)
    viva = result.scalars().first()
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )

    viva.questions.sort(key=lambda q: q.order_index)
    return viva


async def update_viva(db: AsyncSession, viva_id, data: VivaUpdate, user_id) -> Viva:
    stmt = select(Viva).where(Viva.id == viva_id, Viva.owner_id == user_id)
    result = await db.execute(stmt)
    viva = result.scalars().first()
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )

    if data.name is not None:
        viva.name = data.name
    if data.start_time is not None:
        viva.start_time = data.start_time
    if data.end_time is not None:
        viva.end_time = data.end_time

    await db.commit()
    await db.refresh(viva)
    return viva


async def delete_viva(db: AsyncSession, viva_id, user_id):
    stmt = select(Viva).where(Viva.id == viva_id, Viva.owner_id == user_id)
    result = await db.execute(stmt)
    viva = result.scalars().first()
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )

    await db.delete(viva)
    await db.commit()
