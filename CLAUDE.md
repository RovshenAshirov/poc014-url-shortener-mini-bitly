# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

POC-014 is a URL shortener service ("snip.uz") with a FastAPI backend, React + Tailwind frontend, and a three-store data layer: PostgreSQL (URL records), Redis (cache + click counters), and ClickHouse (click event analytics). Short codes are Base62 encodings of `row_count + 1_000_000`.

## Commands

### Backend

```bash
# Activate virtualenv (required before any backend commands)
source venv/bin/activate

# Run backend dev server (from repo root)
uvicorn backend.app.main:app --reload

# Run tests
pytest tests/

# Run a single test
pytest tests/test_base62.py::test_encode_basic

# Database migrations (PostgreSQL only, from repo root)
alembic revision --autogenerate -m "description"
alembic upgrade head

# Load testing
locust -f tests/locustfile.py --host=http://localhost:8000
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

### Data flow

**Shorten** (`POST /api/v1/shorten`): validates URL → deduplicates against PostgreSQL → writes to PostgreSQL → caches in Redis with TTL.

**Redirect** (`GET /{short_code}`): Redis lookup → 302 redirect + `INCR clicks:{short_code}` + background task logs to ClickHouse. On Redis miss, falls back to PostgreSQL, re-caches, then logs.

**Stats** (`GET /api/v1/stats/{short_code}`): PostgreSQL for URL metadata + ClickHouse for `total_clicks` / `today_clicks`.

**Analytics** (`GET /api/v1/analytics/{short_code}/timeseries|geo|referrers`): pure ClickHouse queries.

**WebSocket** (`/ws/stats/{short_code}`): polls ClickHouse every 5 seconds and streams `{total_clicks, today_clicks}` to the client.

### Click event pipeline

`redirect.py` fires `services/analytics.log_click()` as a FastAPI `BackgroundTask`. That function inserts a row into `poc014.click_events` (ClickHouse) with anonymized IP (`/24` prefix), extracted referrer domain, and hardcoded `country_code="UZ"`. Errors are swallowed so analytics never block redirects.

### Key modules

- `backend/app/core/base62.py` — encode/decode integers ↔ Base62 strings.
- `backend/app/core/cache.py` — lazy singleton `redis.asyncio` client.
- `backend/app/core/rate_limit.py` — Redis-backed sliding-window rate limiter (currently commented out in `shorten.py`).
- `backend/app/core/config.py` — Pydantic `Settings` from `backend/.env` (or `.env` at cwd); exposes `DATABASE_URL` as a computed property from individual `POSTGRESQL_*` fields.
- `backend/app/db/models.py` — `URL` table: `id`, `short_code`, `long_url`, `is_custom`, `click_count`, `created_at`, `expires_at`.
- `backend/app/db/clickhouse.py` — synchronous `clickhouse_connect` singleton; `init_clickhouse()` creates the DB and `click_events` table on startup (MergeTree, TTL 1 year).

### Frontend

Three React components:
- `App.jsx` — shorten form, manages selected link state, composes the page.
- `LinksList.jsx` — fetches `/api/v1/links` (last 20), each row is clickable to select a link.
- `Dashboard.jsx` — shows live stats via WebSocket + Chart.js timeseries + geo/referrer breakdowns; connects to `ws://localhost:8000/ws/stats/{short_code}`.

Vite proxies `/api` and `/health` to `localhost:8000` in dev.

**Alembic** is configured at the repo root; `alembic/env.py` loads `backend/.env` and imports models from `backend/`.

## Environment

`backend/.env` (or `.env` at the working directory when running uvicorn from repo root):

```
SECRET_KEY=poc014-secret-key-change-in-prod
BASE_URL=http://localhost:8000

REDIS_URL=redis://localhost:6379

POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_USER=poc014user
POSTGRESQL_PASSWORD=poc014pass
POSTGRESQL_DB=poc014

CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DB=poc014
```

PostgreSQL, Redis, and ClickHouse must all be running before starting the backend. ClickHouse schema is auto-created on startup via `init_clickhouse()`.
