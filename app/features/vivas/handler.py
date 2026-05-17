from sqlalchemy.ext.asyncio import AsyncSession

from app.features.vivas import service
from app.features.vivas.schema import VivaCreate, VivaUpdate


async def handle_create_viva(data: VivaCreate, db: AsyncSession, current_user):
    return await service.create_viva(db, data, current_user.id)


async def handle_get_vivas(db: AsyncSession, current_user):
    return await service.get_vivas(db, current_user.id)


async def handle_get_viva(viva_id, db: AsyncSession, current_user):
    return await service.get_viva_by_id(db, viva_id, current_user.id)


async def handle_update_viva(viva_id, data: VivaUpdate, db: AsyncSession, current_user):
    return await service.update_viva(db, viva_id, data, current_user.id)


async def handle_delete_viva(viva_id, db: AsyncSession, current_user):
    await service.delete_viva(db, viva_id, current_user.id)
