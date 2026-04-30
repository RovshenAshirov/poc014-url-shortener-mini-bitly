import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.clickhouse import init_clickhouse, close_clickhouse, get_clickhouse
from app.db.database import engine, Base
from app.core.cache import close_redis
from app.api.v1 import shorten, redirect, stats, analytics
from app.services.analytics import flush_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # PostgreSQL
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # ClickHouse
    await init_clickhouse()
    flush_task = asyncio.create_task(flush_worker())
    yield
    flush_task.cancel()
    # Shutdown
    await close_redis()
    await close_clickhouse()
    await engine.dispose()

app = FastAPI(
    title="POC-014 URL Shortener",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shorten.router, prefix="/api/v1")
app.include_router(redirect.router)
app.include_router(stats.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "poc014-url-shortener"}


@app.websocket("/ws/stats/{short_code}")
async def websocket_stats(websocket: WebSocket, short_code: str):
    await websocket.accept()
    try:
        while True:
            client = get_clickhouse()

            # Jami clicklar
            total = client.query(f"""
                SELECT COUNT(*) FROM {settings.CLICKHOUSE_DB}.click_events
                WHERE short_code = '{short_code}'
            """)

            # Bugungi clicklar
            today = client.query(f"""
                SELECT COUNT(*) FROM {settings.CLICKHOUSE_DB}.click_events
                WHERE short_code = '{short_code}'
                  AND toDate(event_time) = today()
            """)

            await websocket.send_json({
                "short_code": short_code,
                "total_clicks": total.result_rows[0][0],
                "today_clicks": today.result_rows[0][0],
            })

            # 5 soniyada bir yangilanadi
            await asyncio.sleep(5)
    except Exception:
        await websocket.close()
