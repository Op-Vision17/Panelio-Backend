import redis.asyncio as redis
from app.core.config import settings

class RedisClient:
    _instance = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = await redis.from_url(
                settings.REDIS_URL, decode_responses=True
            )
        return cls._instance

async def get_redis():
    return await RedisClient.get_instance()
