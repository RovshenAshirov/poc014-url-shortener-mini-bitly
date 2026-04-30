from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import URL
from app.core.cache import get_redis

router = APIRouter()

@router.get("/{short_code}")
async def redirect_url(short_code: str, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()

    # 1. Redis dan qidiramiz (tez yo'l)
    cached = await redis.get(f"url:{short_code}")
    if cached:
        await redis.incr(f"clicks:{short_code}")
        return RedirectResponse(url=cached, status_code=302)

    # 2. PostgreSQL dan qidiramiz
    url = await db.scalar(select(URL).where(URL.short_code == short_code))

    if not url:
        raise HTTPException(status_code=404, detail="URL topilmadi")

    # Muddati tekshirish
    if url.expires_at and url.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="URL muddati o'tgan")

    # Redis ga kesh qilamiz (keyingi so'rov uchun)
    await redis.setex(f"url:{short_code}", 86400, url.long_url)
    await redis.incr(f"clicks:{short_code}")

    return RedirectResponse(url=url.long_url, status_code=302)
