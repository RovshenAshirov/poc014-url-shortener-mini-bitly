# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

POC-014 is a URL shortener service ("snip.uz") with a FastAPI + PostgreSQL + Redis backend and a React + Tailwind frontend. Short codes are generated via Base62 encoding of an auto-incremented DB row ID offset by 1,000,000.

## Commands

### Backend

```bash
# Activate virtualenv (required before running any backend commands)
source venv/bin/activate

# Run backend dev server (from repo root)
uvicorn backend.app.main:app --reload

# Run tests
pytest tests/

# Run a single test
pytest tests/test_base62.py::test_encode_basic

# Database migrations (from repo root)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # dev server with proxy to localhost:8000
npm run build
npm run lint
```

## Architecture

The backend is a single FastAPI app (`backend/app/main.py`) that mounts two routers:

- `POST /api/v1/shorten` — validates URL, generates or accepts a custom alias, stores in PostgreSQL, caches in Redis, returns the short URL.
- `GET /{short_code}` — checks Redis first (cache hit → 302 redirect + incr click counter), falls back to PostgreSQL, re-caches on miss, returns 410 if expired.

**Key modules:**
- `backend/app/core/base62.py` — encode/decode between integers and Base62 strings; short codes are `encode(row_count + 1_000_000)`.
- `backend/app/core/cache.py` — lazy singleton Redis client using `redis.asyncio`.
- `backend/app/core/config.py` — Pydantic `Settings` loaded from `backend/.env`: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `BASE_URL`.
- `backend/app/db/models.py` — single `URL` table: `id`, `short_code`, `long_url`, `is_custom`, `click_count`, `created_at`, `expires_at`.

**Frontend** (`frontend/src/App.jsx`) is a single-component React app that calls `/api/v1/shorten`. Vite proxies `/api` and `/health` to `localhost:8000` in dev.

**Alembic** is configured at the repo root; `alembic/env.py` loads `backend/.env` and imports models from `backend/`.

## Environment

Copy `backend/.env` values for local dev:
```
DATABASE_URL=postgresql+asyncpg://poc014user:poc014pass@localhost:5432/poc014
REDIS_URL=redis://localhost:6379
SECRET_KEY=poc014-secret-key-change-in-prod
BASE_URL=http://localhost:8000
```

PostgreSQL and Redis must be running locally before starting the backend.
