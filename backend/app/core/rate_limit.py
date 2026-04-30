from fastapi import HTTPException, Request
from app.core.cache import get_redis

async def check_rate_limit(request: Request, limit: int = 100, window: int = 3600):
    redis = await get_redis()
    ip = request.client.host
    key = f"rate:{ip}"

    count = await redis.incr(key)

    # Birinchi so'rovda TTL o'rnatamiz
    if count == 1:
        await redis.expire(key, window)

    if count > limit:
        remaining = await redis.ttl(key)
        raise HTTPException(
            status_code=429,
            detail=f"Limitdan oshdingiz. {remaining} soniyadan keyin urinib ko'ring"
        )
