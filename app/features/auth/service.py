import hashlib
import random
import string
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_otp,
    verify_otp_hash,
    verify_token,
)
from app.features.auth.dao import AuthDAO
from app.features.auth.model import RefreshToken, User
from app.shared.exceptions import BadRequestError, UnauthorizedError


async def generate_and_store_otp(email: str, redis) -> str:
    otp = "".join(random.choices(string.digits, k=6))
    otp_hash = hash_otp(otp)
    await redis.set(f"otp:{email}", otp_hash, ex=300)  # 5 min TTL
    return otp


async def verify_and_consume_otp(email: str, otp: str, redis) -> bool:
    otp_hash = await redis.get(f"otp:{email}")
    if not otp_hash:
        return False

    if verify_otp_hash(otp, otp_hash):
        await redis.delete(f"otp:{email}")
        return True
    return False


async def get_or_create_user(email: str, db: AsyncSession) -> User:
    auth_dao = AuthDAO(db)
    user = await auth_dao.get_user_by_email(email)

    if not user:
        user = User(email=email)
        user = await auth_dao.create_user(user)

    return user


async def create_token_pair(user_id: str, db: AsyncSession) -> tuple[str, str]:
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    # In security.py we used jwt.decode to verify, so we can use jwt.decode here too to get expiry
    from jose import jwt

    from app.core.config import settings

    payload = jwt.decode(
        refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    new_refresh_token = RefreshToken(
        user_id=user_id, token_hash=token_hash, expires_at=expires_at
    )
    auth_dao = AuthDAO(db)
    await auth_dao.create_refresh_token(new_refresh_token)

    return access_token, refresh_token


async def rotate_refresh_token(token: str, db: AsyncSession) -> tuple[str, str]:
    payload = verify_token(token)
    user_id = payload.get("sub")

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    auth_dao = AuthDAO(db)
    db_token = await auth_dao.get_refresh_token_by_hash(token_hash)

    if (
        not db_token
        or db_token.revoked
        or db_token.expires_at < datetime.now(timezone.utc)
    ):
        raise UnauthorizedError("Invalid or expired refresh token")

    # Revoke old token
    db_token.revoked = True
    await auth_dao.save_changes()

    # Create new pair
    return await create_token_pair(user_id, db)


async def revoke_refresh_token(token: str, db: AsyncSession):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    auth_dao = AuthDAO(db)
    db_token = await auth_dao.get_refresh_token_by_hash(token_hash)

    if db_token:
        db_token.revoked = True
        await auth_dao.save_changes()
