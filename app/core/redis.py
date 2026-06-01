import redis.asyncio as redis

from app.core.config import settings


class RedisClient:
    _instance = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
                from upstash_redis.asyncio import Redis
                cls._instance = Redis(
                    url=settings.UPSTASH_REDIS_REST_URL,
                    token=settings.UPSTASH_REDIS_REST_TOKEN
                )
            else:
                cls._instance = await redis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
        return cls._instance


async def get_redis():
    return await RedisClient.get_instance()
