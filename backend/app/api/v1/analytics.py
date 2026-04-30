from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.clickhouse import get_clickhouse
from app.core.config import settings

router = APIRouter()

# ─── Timeseries ───────────────────────────────────────

class TimeseriesItem(BaseModel):
    date: str
    clicks: int

@router.get("/analytics/{short_code}/timeseries",
            response_model=list[TimeseriesItem])
async def get_timeseries(short_code: str, days: int = 7):
    client = get_clickhouse()
    result = client.query(f"""
        SELECT
            toString(toDate(event_time)) as date,
            COUNT(*) as clicks
        FROM {settings.CLICKHOUSE_DB}.click_events
        WHERE short_code = '{short_code}'
          AND event_time >= now() - INTERVAL {days} DAY
        GROUP BY date
        ORDER BY date ASC
    """)
    return [
        TimeseriesItem(date=row[0], clicks=row[1])
        for row in result.result_rows
    ]

# ─── Geo ──────────────────────────────────────────────

class GeoItem(BaseModel):
    country_code: str
    clicks: int
    pct: float

@router.get("/analytics/{short_code}/geo",
            response_model=list[GeoItem])
async def get_geo(short_code: str):
    client = get_clickhouse()
    result = client.query(f"""
        SELECT
            country_code,
            COUNT(*) as clicks,
            round(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
        FROM {settings.CLICKHOUSE_DB}.click_events
        WHERE short_code = '{short_code}'
        GROUP BY country_code
        ORDER BY clicks DESC
    """)
    return [
        GeoItem(country_code=row[0], clicks=row[1], pct=row[2])
        for row in result.result_rows
    ]

# ─── Referrers ────────────────────────────────────────

class ReferrerItem(BaseModel):
    domain: str
    clicks: int
    pct: float

@router.get("/analytics/{short_code}/referrers",
            response_model=list[ReferrerItem])
async def get_referrers(short_code: str):
    client = get_clickhouse()
    result = client.query(f"""
        SELECT
            referrer as domain,
            COUNT(*) as clicks,
            round(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
        FROM {settings.CLICKHOUSE_DB}.click_events
        WHERE short_code = '{short_code}'
        GROUP BY domain
        ORDER BY clicks DESC
        LIMIT 10
    """)
    return [
        ReferrerItem(domain=row[0], clicks=row[1], pct=row[2])
        for row in result.result_rows
    ]
