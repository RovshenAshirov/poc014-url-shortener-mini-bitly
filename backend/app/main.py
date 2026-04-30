from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.core.cache import close_redis
from app.api.v1 import shorten, redirect

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start: jadvallarni yaratish
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Stop: ulanishlarni yopish
    await close_redis()
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

@app.get("/health")
async def health():
    return {"status": "ok", "service": "poc014-url-shortener"}
