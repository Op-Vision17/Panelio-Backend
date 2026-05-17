import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.vivas import handler
from app.features.vivas.schema import (
    VivaCreate,
    VivaDetailResponse,
    VivaResponse,
    VivaUpdate,
)
from app.shared.dependencies import get_current_user

router = APIRouter()


@router.post("", response_model=VivaResponse, status_code=status.HTTP_201_CREATED)
async def create_viva(
    data: VivaCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_create_viva(data, db, current_user)


@router.get("", response_model=List[VivaResponse])
async def get_vivas(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    return await handler.handle_get_vivas(db, current_user)


@router.get("/{viva_id}", response_model=VivaDetailResponse)
async def get_viva(
    viva_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_get_viva(viva_id, db, current_user)


@router.patch("/{viva_id}", response_model=VivaResponse)
async def update_viva(
    viva_id: uuid.UUID,
    data: VivaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_update_viva(viva_id, data, db, current_user)


@router.delete("/{viva_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_viva(
    viva_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await handler.handle_delete_viva(viva_id, db, current_user)
