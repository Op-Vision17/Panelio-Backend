import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.auth.model import RefreshToken, User


class AuthDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id) -> User | None:
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def create_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.commit()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def save_changes(self) -> None:
        await self.db.commit()
