# POC-014 Sprint 2 — Analytika va Xavfsizlik

**Muallif:** Rovshen R. Ashirov  
**Loyiha:** POC-014 URL Shortener  
**Sana:** Aprel 2026  
**Holat:** ✅ Tugallandi

---

## Maqsad

Sprint 1 da asosiy redirect ishlagan edi. Sprint 2 da:
- Har bir click ni ClickHouse ga yozish
- Statistika API
- Rate limiting (spam himoyasi)
- QR code generator

---

## Bajarilgan ishlar

| # | Vazifa | Holat |
|---|--------|-------|
| 1 | ClickHouse o'rnatish va sozlash | ✅ |
| 2 | `poc014user` yaratish | ✅ |
| 3 | `click_events` jadvali | ✅ |
| 4 | Click event logger | ✅ |
| 5 | GET /api/v1/stats/{code} | ✅ |
| 6 | Rate limiting | ✅ |
| 7 | QR code generator (frontend) | ✅ |

---

## 1. ClickHouse o'rnatish

### Nima uchun ClickHouse?

```
PostgreSQL — OLTP (tez, kichik so'rovlar)
ClickHouse — OLAP (katta ma'lumot tahlili)

100 million click_events:
  PostgreSQL → "30 kunlik grafik?" → 60 soniya ❌
  ClickHouse → xuddi shu so'rov   → 0.1 soniya ✅
```

### O'rnatish buyruqlari

```bash
# 1. HTTPS transport
sudo apt install -y apt-transport-https ca-certificates curl

# 2. ClickHouse GPG kaliti
curl -fsSL https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg

# 3. Repo qo'shish
echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] \
  https://packages.clickhouse.com/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/clickhouse.list

# 4. O'rnatish
sudo apt update
sudo apt install -y clickhouse-server clickhouse-client

# 5. Ishga tushirish
sudo clickhouse start

# 6. Tekshirish
clickhouse-client --query "SELECT version()"
# → 26.3.9.8
```

### Python driver

```bash
pip install clickhouse-connect
```

`clickhouse-connect` — Python dan ClickHouse ga HTTP orqali ulanadi.

---

## 2. `poc014user` yaratish

### Nima uchun yangi user?

```
default user → parolsiz → PyCharm ulanolmadi
poc014user   → parol bilan → to'g'ri ulanish
```

### Buyruqlar

```bash
# User yaratish
clickhouse-client --query \
  "CREATE USER poc014user IDENTIFIED WITH plaintext_password BY 'poc014pass'"

# Huquq berish — faqat poc014 database ga
clickhouse-client --query \
  "GRANT ALL ON poc014.* TO poc014user"
```

### PyCharm ulanish sozlamalari

```
Host:     localhost
Port:     8123
User:     poc014user
Password: poc014pass
Database: poc014
Driver:   ClickHouse (HTTP)
```

---

## 3. `.env` va `config.py` yangilash

### `.env`

```env
# PostgreSQL
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_USER=poc014user
POSTGRESQL_PASSWORD=poc014pass
POSTGRESQL_DB=poc014

# Redis
REDIS_URL=redis://localhost:6379

# App
SECRET_KEY=poc014-secret-key-change-in-prod
BASE_URL=http://localhost:8000

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=poc014user
CLICKHOUSE_PASSWORD=poc014pass
CLICKHOUSE_DB=poc014
```

### `config.py`

```python
class Settings(BaseSettings):
    # PostgreSQL — alohida parametrlar
    POSTGRESQL_HOST: str = "localhost"
    POSTGRESQL_PORT: int = 5432
    POSTGRESQL_USER: str
    POSTGRESQL_PASSWORD: str
    POSTGRESQL_DB: str

    # Redis
    REDIS_URL: str

    # App
    SECRET_KEY: str
    BASE_URL: str = "http://localhost:8000"

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_DB: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRESQL_USER}:{self.POSTGRESQL_PASSWORD}"
            f"@{self.POSTGRESQL_HOST}:{self.POSTGRESQL_PORT}"
            f"/{self.POSTGRESQL_DB}"
        )
```

**Muhim o'zgarish:** `DATABASE_URL` endi `.env` dan to'g'ridan-to'g'ri o'qilmaydi. `@property` orqali avtomatik quriladi:
```
POSTGRESQL_* → DATABASE_URL = postgresql+asyncpg://user:pass@host:port/db
```

---

## 4. `clickhouse.py` — ClickHouse client

**Fayl:** `backend/app/db/clickhouse.py`

```python
import clickhouse_connect
from clickhouse_connect.driver.client import Client
from app.core.config import settings

_client: Client | None = None

def get_clickhouse() -> Client:
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
        )
    return _client

async def init_clickhouse():
    client = get_clickhouse()

    # 1. Database yaratish
    client.command(f"CREATE DATABASE IF NOT EXISTS {settings.CLICKHOUSE_DB}")

    # 2. Jadval yaratish
    client.command(f"""
        CREATE TABLE IF NOT EXISTS {settings.CLICKHOUSE_DB}.click_events (
            event_time   DateTime,
            short_code   String,
            country_code String,
            referrer     String,
            ip_prefix    String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(event_time)
        ORDER BY (short_code, event_time)
        TTL event_time + INTERVAL 1 YEAR
    """)

async def close_clickhouse():
    global _client
    if _client:
        _client.close()
        _client = None
```

### Tushuntirish

```
get_clickhouse()
  → Singleton pattern
  → Bir marta ulanadi, qayta ishlatiladi
  → _client = None bo'lsa → yangi ulanish ochadi
  → Bor bo'lsa → mavjudini qaytaradi

init_clickhouse()
  → FastAPI server yonganda chaqiriladi (lifespan)
  → CREATE DATABASE IF NOT EXISTS → bor bo'lsa qayta yaratmaydi
  → CREATE TABLE IF NOT EXISTS   → bor bo'lsa qayta yaratmaydi

close_clickhouse()
  → Server o'chganda chaqiriladi
  → Ulanishni yopadi
```

### `click_events` jadvali tuzilmasi

```sql
CREATE TABLE poc014.click_events (
    event_time   DateTime,   -- Qachon bosildi
    short_code   String,     -- Qaysi URL (4C92, gov-portal)
    country_code String,     -- Qaysi davlat (UZ, RU, KZ)
    referrer     String,     -- Qayerdan keldi (google.com, telegram)
    ip_prefix    String      -- Qaysi IP (/24 anonymized: 192.168.1)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)   -- Oyma-oy bo'linadi
ORDER BY (short_code, event_time)   -- Tez qidirish uchun
TTL event_time + INTERVAL 1 YEAR   -- 1 yildan keyin o'chadi
```

**MergeTree** — ClickHouse ning asosiy engine:
```
Yangi ma'lumot → yoziladi
Fonda          → kichik qismlar birlashtirilib optimizatsiya qilinadi
Natija         → juda tez o'qish
```

---

## 5. `main.py` yangilash — lifespan

```python
from app.db.clickhouse import init_clickhouse, close_clickhouse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Server yonganda:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # PostgreSQL
    await init_clickhouse()                             # ClickHouse
    yield
    # Server o'chganda:
    await close_redis()
    await close_clickhouse()
    await engine.dispose()
```

**Oqim:**
```
Server yondi
    ↓
PostgreSQL: urls jadvali bor? → yo'q → yaratdi
ClickHouse: poc014 DB bor?    → yo'q → yaratdi
ClickHouse: click_events bor? → yo'q → yaratdi
    ↓
Server ishlayapti ✅
    ↓
Server o'chdi
    ↓
Redis ulanish yopildi
ClickHouse ulanish yopildi
PostgreSQL pool yopildi
```

---

## 6. `analytics.py` — Click logger

**Fayl:** `backend/app/services/analytics.py`

```python
from datetime import datetime
from app.db.clickhouse import get_clickhouse

async def log_click(short_code: str, ip: str, referrer: str):
    try:
        # IP anonymize: 192.168.1.100 → 192.168.1
        ip_prefix = ".".join(ip.split(".")[:3]) if ip else "unknown"

        # Referrer domenini ajratish
        # https://google.com/search?q=... → google.com
        if referrer and "://" in referrer:
            referrer_domain = referrer.split("://")[1].split("/")[0]
        elif referrer:
            referrer_domain = referrer
        else:
            referrer_domain = "direct"

        client = get_clickhouse()
        client.insert(
            "poc014.click_events",
            [[datetime.now(), short_code, "UZ", referrer_domain, ip_prefix]],
            column_names=["event_time", "short_code", "country_code",
                         "referrer", "ip_prefix"]
        )
    except Exception as e:
        # Analytics xatosi redirect ni to'xtatmasin!
        print(f"Analytics error: {e}")
```

### Tushuntirish

```
IP anonymize nima uchun?
  192.168.1.100 → to'liq IP saqlamaslik (GDPR, maxfiylik)
  192.168.1     → /24 prefix yetarli geo tahlil uchun

Referrer domain nima uchun?
  https://google.com/search?q=poc014 → google.com
  Butun URL saqlamaslik → faqat domen kerak

try/except nima uchun?
  ClickHouse xato bersa → redirect to'xtamasin
  Analytics muhim, lekin redirect undan muhimroq
```

---

## 7. `redirect.py` yangilash — Background task

```python
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from app.services.analytics import log_click

@router.get("/{short_code}")
async def redirect_url(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    redis = await get_redis()

    # IP va referrer olish
    ip = request.client.host
    referrer = request.headers.get("referer", "")

    # 1. Redis dan qidiramiz
    cached = await redis.get(f"url:{short_code}")
    if cached:
        await redis.incr(f"clicks:{short_code}")
        background_tasks.add_task(log_click, short_code, ip, referrer)
        return RedirectResponse(url=cached, status_code=302)

    # 2. PostgreSQL dan qidiramiz
    url = await db.scalar(select(URL).where(URL.short_code == short_code))

    if not url:
        raise HTTPException(status_code=404, detail="URL topilmadi")

    if url.expires_at and url.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="URL muddati o'tgan")

    await redis.setex(f"url:{short_code}", 86400, url.long_url)
    await redis.incr(f"clicks:{short_code}")
    background_tasks.add_task(log_click, short_code, ip, referrer)

    return RedirectResponse(url=url.long_url, status_code=302)
```

### Async oqim

```
GET /4C92 keldi
    ↓
Redis → HIT → 0.8ms
    ↓
background_tasks.add_task(log_click, ...)
← Bu yerda foydalanuvchi redirect oldi (0.8ms) ✅
    ↓
Orqada (foydalanuvchi kutmaydi):
  log_click() → ClickHouse ga INSERT (~5ms)
```

**BackgroundTasks** — FastAPI built-in:
```
Response qaytarilgandan KEYIN bajariladi
Foydalanuvchi kutmaydi
Server resurslarini band qilmaydi
```

---

## 8. `stats.py` — Statistika endpoint

**Fayl:** `backend/app/api/v1/stats.py`

```python
@router.get("/stats/{short_code}", response_model=StatsResponse)
async def get_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    # PostgreSQL dan URL ma'lumotlari
    url = await db.scalar(select(URL).where(URL.short_code == short_code))
    if not url:
        raise HTTPException(status_code=404, detail="URL topilmadi")

    client = get_clickhouse()

    # Jami clicklar
    total = client.query(f"""
        SELECT COUNT(*) FROM {settings.CLICKHOUSE_DB}.click_events
        WHERE short_code = '{short_code}'
    """)
    total_clicks = total.result_rows[0][0] if total.result_rows else 0

    # Bugungi clicklar
    today = client.query(f"""
        SELECT COUNT(*) FROM {settings.CLICKHOUSE_DB}.click_events
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
```

### Test natijasi

```json
GET /api/v1/stats/4C92

{
  "short_code": "4C92",
  "short_url": "http://localhost:8000/4C92",
  "long_url": "https://uzinfocom.uz/projects/...",
  "total_clicks": 1,
  "today_clicks": 1,
  "created_at": "2026-04-29T11:13:55.746636Z",
  "expires_at": null
}
```

---

## 9. `rate_limit.py` — Spam himoyasi

**Fayl:** `backend/app/core/rate_limit.py`

```python
from fastapi import HTTPException, Request
from app.core.cache import get_redis

async def check_rate_limit(request: Request, limit: int = 100, window: int = 3600):
    redis = await get_redis()
    ip = request.client.host
    key = f"rate:{ip}"

    count = await redis.incr(key)      # +1 qo'shadi (atomic)

    if count == 1:
        await redis.expire(key, window) # 1-chi so'rovda TTL o'rnatadi

    if count > limit:
        remaining = await redis.ttl(key)
        raise HTTPException(
            status_code=429,
            detail=f"Limitdan oshdingiz. {remaining} soniyadan keyin urinib ko'ring"
        )
```

### Qanday ishlaydi

```
1-chi so'rov:
  redis.incr("rate:127.0.0.1") → 1
  redis.expire(..., 3600)       → TTL = 1 soat

50-chi so'rov:
  redis.incr("rate:127.0.0.1") → 50
  50 < 100 → o'tkazib yuboradi ✅

101-chi so'rov:
  redis.incr("rate:127.0.0.1") → 101
  101 > 100 → 429 Too Many Requests ❌
  "Limitdan oshdingiz. 3548 soniyadan keyin urinib ko'ring"

1 soat o'tgach:
  Redis TTL → "rate:127.0.0.1" o'chadi
  Qayta 100 ta so'rov huquqi beriladi
```

### Redis da tekshirish

```bash
redis-cli GET "rate:127.0.0.1"
# → "1"

redis-cli TTL "rate:127.0.0.1"
# → 3548 (soniya)
```

---

## 10. QR code generator (Frontend)

### O'rnatish

```bash
npm install qrcode
```

### `App.jsx` o'zgartirishlar

**Import:**
```jsx
import QRCode from 'qrcode'
import { useState, useEffect, useRef } from 'react'
```

**useRef qo'shish:**
```jsx
const canvasRef = useRef(null)
// Canvas elementiga to'g'ridan-to'g'ri murojaat qilish uchun
```

**QR generatsiya — setTimeout bilan:**
```jsx
setResult(data)
setTimeout(() => {
  if (canvasRef.current) {
    QRCode.toCanvas(canvasRef.current, data.short_url, {
      width: 160,
      margin: 2,
      color: { dark: '#1d4ed8', light: '#ffffff' }
    })
  }
}, 100)
```

**Nima uchun setTimeout(100)?**
```
setResult(data) → React state yangilanadi
Canvas DOM da paydo bo'lishi uchun vaqt kerak
100ms → React render tugashini kutadi
Keyin canvasRef.current mavjud bo'ladi
```

**PNG yuklab olish:**
```jsx
const link = document.createElement('a')
link.download = `qr-${result.short_code}.png`
link.href = canvasRef.current.toDataURL()  // Canvas → base64 PNG
link.click()
```

**SVG yuklab olish:**
```jsx
const svgData = `<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>
  <image href='${canvasRef.current.toDataURL()}' width='160' height='160'/>
</svg>`
const blob = new Blob([svgData], { type: 'image/svg+xml' })
const link = document.createElement('a')
link.download = `qr-${result.short_code}.svg`
link.href = URL.createObjectURL(blob)
link.click()
```

---

## Umumiy oqim — Sprint 2 da

```
Foydalanuvchi → /4C92 ga kirdi
      ↓
Redis → HIT → 0.8ms → 302 redirect ✅
      ↓ (parallel, orqada)
log_click() → background task
  IP: 192.168.1.100 → 192.168.1 (anonymized)
  Referrer: https://google.com → google.com
  ClickHouse INSERT:
    {2026-04-30 11:45:01, 4C92, UZ, google.com, 192.168.1}
      ↓
GET /api/v1/stats/4C92
  PostgreSQL → URL ma'lumotlari
  ClickHouse → COUNT(*) = 42 clicks
  Response: {total_clicks: 42, today_clicks: 5, ...}
```

---

## Tekshirish

```bash
# ClickHouse da click_events borligini tekshirish
clickhouse-client \
  --user poc014user \
  --password poc014pass \
  --query "SELECT * FROM poc014.click_events LIMIT 10"

# Natija:
# 2026-04-30 11:45:01  4C92     UZ  127.0.0.1:8000  127.0.0
# 2026-04-30 11:45:16  rovshen  UZ  127.0.0.1:8000  127.0.0

# Rate limit tekshirish
redis-cli GET "rate:127.0.0.1"   # → "1"
redis-cli TTL "rate:127.0.0.1"   # → 3548
```

---

## Definition of Done

| Mezon | Natija |
|-------|--------|
| ClickHouse ishga tushdi | ✅ v26.3.9.8 |
| click_events jadvali yaratildi | ✅ FastAPI lifespan orqali |
| Redirect da click yozilmoqda | ✅ |
| Stats API ishlaydi | ✅ |
| Rate limiting ishlaydi | ✅ 100 req/soat |
| QR code chiqmoqda | ✅ PNG + SVG |

---

## Navbatdagi qadam — Sprint 3

- Analytics dashboard (grafik, geo, referrer)
- WebSocket — real-time yangilanish
- GeoIP — IP dan davlat kodi
- Links ro'yxati UI

---

*POC-014 · Uzinfocom R&D · Sprint 2 · Aprel 2026*