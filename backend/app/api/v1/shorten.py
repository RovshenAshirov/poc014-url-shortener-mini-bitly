from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import validators

from app.db.database import get_db
from app.db.models import URL
from app.core.base62 import encode
from app.core.cache import get_redis
from app.core.config import settings

router = APIRouter()

class ShortenRequest(BaseModel):
    long_url: str
    alias: str | None = None
    ttl_days: int | None = None

class ShortenResponse(BaseModel):
    short_url: str
    short_code: str
    long_url: str
    expires_at: datetime | None = None

@router.post("/shorten", response_model=ShortenResponse)
async def shorten_url(req: ShortenRequest, db: AsyncSession = Depends(get_db)):
    # URL tekshirish
    if not validators.url(req.long_url):
        raise HTTPException(status_code=400, detail="Noto'g'ri URL format")

    # Alias tekshirish
    if req.alias:
        existing = await db.scalar(select(URL).where(URL.short_code == req.alias))
        if existing:
            raise HTTPException(status_code=409, detail="Bu alias band")
        short_code = req.alias
        is_custom = True
    else:
        # Avval xuddi shu URL bor-yo'qligini tekshiramiz
        existing = await db.scalar(
            select(URL).where(URL.long_url == req.long_url, URL.is_custom == False)
        )
        if existing:
            return ShortenResponse(
                short_url=f"{settings.BASE_URL}/{existing.short_code}",
                short_code=existing.short_code,
                long_url=existing.long_url,
                expires_at=existing.expires_at,
            )
        # Yangi id olish va Base62 encode
        next_id = await db.scalar(select(func.count()).select_from(URL)) + 1000000
        short_code = encode(next_id)
        is_custom = False

    # TTL hisoblash
    expires_at = None
    if req.ttl_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.ttl_days)

    # DB ga saqlash
    url = URL(
        short_code=short_code,
        long_url=req.long_url,
        is_custom=is_custom,
        expires_at=expires_at,
    )
    db.add(url)
    await db.commit()

    # Redis ga kesh
    redis = await get_redis()
    ttl = req.ttl_days * 86400 if req.ttl_days else 86400
    await redis.setex(f"url:{short_code}", ttl, req.long_url)

    return ShortenResponse(
        short_url=f"{settings.BASE_URL}/{short_code}",
        short_code=short_code,
        long_url=req.long_url,
        expires_at=expires_at,
    )
