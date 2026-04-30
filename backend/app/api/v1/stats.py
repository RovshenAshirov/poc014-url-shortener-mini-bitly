from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import URL
from app.db.clickhouse import get_clickhouse
from app.core.config import settings

router = APIRouter()

class StatsResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    total_clicks: int
    today_clicks: int
    created_at: datetime
    expires_at: datetime | None

@router.get("/stats/{short_code}", response_model=StatsResponse)
async def get_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    # PostgreSQL dan URL ma'lumotlarini olamiz
    url = await db.scalar(select(URL).where(URL.short_code == short_code))
    if not url:
        raise HTTPException(status_code=404, detail="URL topilmadi")

    # ClickHouse dan click statistikasini olamiz
    client = get_clickhouse()

    # Jami clicklar
    total = client.query(f"""
        SELECT COUNT(*) as cnt
        FROM {settings.CLICKHOUSE_DB}.click_events
        WHERE short_code = '{short_code}'
    """)
    total_clicks = total.result_rows[0][0] if total.result_rows else 0

    # Bugungi clicklar
    today = client.query(f"""
        SELECT COUNT(*) as cnt
        FROM {settings.CLICKHOUSE_DB}.click_events
        WHERE short_code = '{short_code}'
          AND toDate(event_time) = today()
    """)
    today_clicks = today.result_rows[0][0] if today.result_rows else 0

    return StatsResponse(
        short_code=short_code,
        short_url=f"{settings.BASE_URL}/{short_code}",
        long_url=url.long_url,
        total_clicks=total_clicks,
        today_clicks=today_clicks,
        created_at=url.created_at,
        expires_at=url.expires_at,
    )
