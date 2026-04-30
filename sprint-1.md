# POC-014 Sprint 1 — Poydevor

**Sana:** Aprel 2026  
**Muallif:** Rovshen R. Ashirov  
**Holat:** ✅ Tugallandi

---

## Muhit

| Komponent | Versiya |
|-----------|---------|
| OS | Ubuntu 24.04 LTS |
| Python | 3.12.3 |
| PostgreSQL | 18.3 |
| Redis | 7.0.15 |
| Node.js | 22.22.1 |
| npm | 10.9.4 |

> Docker ishlatilmadi — ongli qaror. Ubuntu 24.04 da to'g'ridan-to'g'ri o'rnatish tanlandi.

---

## Loyiha tuzilmasi

```
poc014-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── shorten.py   # POST /api/v1/shorten
│   │   │       └── redirect.py  # GET /{code}
│   │   ├── core/
│   │   │   ├── base62.py        # ID generatsiya algoritmi
│   │   │   ├── cache.py         # Redis ulanish
│   │   │   └── config.py        # .env sozlamalar
│   │   └── db/
│   │       ├── database.py      # PostgreSQL ulanish
│   │       └── models.py        # urls jadvali
│   └── .env
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 3730a3bcc47f_create_urls_table.py
├── frontend/
│   └── src/
│       ├── App.jsx              # Asosiy UI
│       └── index.css            # Tailwind
├── tests/
│   └── test_base62.py
└── venv/
```

---

## O'rnatilgan Python paketlar

| Paket | Versiya | Nima uchun |
|-------|---------|-----------|
| fastapi | 0.136.1 | API framework |
| uvicorn[standard] | 0.46.0 | ASGI server. `[standard]` = uvloop + websockets |
| sqlalchemy[asyncio] | 2.0.49 | ORM. `[asyncio]` = async PostgreSQL |
| asyncpg | 0.31.0 | PostgreSQL async driver |
| alembic | 1.18.4 | DB migratsiyalar |
| redis[hiredis] | 7.4.0 | Redis client. `[hiredis]` = tezroq parser |
| pydantic-settings | 2.14.0 | .env fayldan sozlamalar o'qish |
| python-dotenv | 1.2.2 | .env faylni yuklash |
| validators | 0.35.0 | URL formatini tekshirish |
| pytest | 9.0.3 | Unit testlar |

---

## Yaratilgan fayllar va tushuntirish

### `backend/app/core/config.py`
`.env` fayldan sozlamalarni o'qiydi. Butun loyiha shu orqali konfiguratsiya oladi.

```python
DATABASE_URL=postgresql+asyncpg://poc014user:poc014pass@localhost:5432/poc014
REDIS_URL=redis://localhost:6379
SECRET_KEY=poc014-secret-key-change-in-prod
BASE_URL=http://localhost:8000
```

Bir joyda o'zgartirish yetarli — hamma joyda o'zgaradi.

---

### `backend/app/core/base62.py`
PostgreSQL `id` raqamini qisqa URL kodga aylantiradi.

**Qanday ishlaydi:**
```
62 ta belgi: 0-9, A-Z, a-z

encode(1000001) → "4C93"   (4 belgi!)
decode("4C93")  → 1000001

6 belgili kod → 56 milliard URL uchun yetadi
```

**Nima uchun Base62:**
- Base64 da `+` va `/` bor → URL da muammo
- Base62 faqat harf va raqam → URL uchun xavfsiz

---

### `backend/app/db/database.py`
PostgreSQL ga async ulanish ochadi.

```
engine          → ulanish pool (10 ta parallel so'rov)
AsyncSessionLocal → har bir API so'rovga alohida session
get_db()        → dependency injection orqali session beradi
Base            → barcha modellar shu classdan meros oladi
```

---

### `backend/app/db/models.py`
`urls` jadvalining Python ko'rinishi.

```
urls jadvali:
┌────────────┬──────────────┬──────────────────┬─────────────┬────────────┐
│ id         │ short_code   │ long_url         │ click_count │ expires_at │
├────────────┼──────────────┼──────────────────┼─────────────┼────────────┤
│ 1000001    │ 4C93         │ https://uzin...  │ 0           │ NULL       │
│ 1000002    │ gov-portal   │ https://my.gov.. │ 0           │ 2026-05-01 │
└────────────┴──────────────┴──────────────────┴─────────────┴────────────┘

id          → bigint, auto increment (SERIAL)
short_code  → varchar(20), UNIQUE index
long_url    → text, cheklovsiz uzunlik
is_custom   → boolean, alias berilganmi
click_count → bigint, nechta marta bosilgan
created_at  → timestamptz, default now()
expires_at  → timestamptz, nullable (TTL uchun)
```

---

### `backend/app/core/cache.py`
Redis ga async ulanish. Singleton pattern — bir marta ulanadi, qayta ishlatiladi.

```
Redis da saqlanadigan kalitlar:

url:{code}     → long URL (TTL: 24 soat)
clicks:{code}  → click counter
```

---

### `backend/app/api/v1/shorten.py`
`POST /api/v1/shorten` — URL qisqartirish logikasi.

**Oqim:**
```
1. URL formatini tekshir (validators)
   "uzinfocom.uz"         → ❌ 400 Bad Request
   "https://uzinfocom.uz" → ✅

2. Alias berilganmi?
   HA  → DB da band emasmi? → band bo'lsa 409 Conflict
   YO'Q → Bu URL avval qisqartirilganmi?
          HA  → mavjud kodni qaytaradi (deduplication)
          YO'Q → encode(count + 1000000) → yangi kod

3. TTL berilganmi?
   7 kun → expires_at = now() + 7 kun
   YO'Q  → expires_at = NULL (doimiy)

4. PostgreSQL ga saqlaydi
5. Redis ga kesh qiladi
6. { short_url, short_code, long_url, expires_at } qaytaradi
```

**So'rov:**
```json
{
  "long_url": "https://uzinfocom.uz/projects/...",
  "alias": "gov-portal",
  "ttl_days": 30
}
```

**Javob:**
```json
{
  "short_url": "http://localhost:8000/4C93",
  "short_code": "4C93",
  "long_url": "https://uzinfocom.uz/projects/...",
  "expires_at": null
}
```

---

### `backend/app/api/v1/redirect.py`
`GET /{code}` — redirect logikasi.

**Oqim:**
```
GET /4C93 keldi

1. Redis dan qidiradi → ~0.8ms
   TOPILDI → clicks:{code}++ → 302 redirect ✅

2. Redis da yo'q → PostgreSQL dan qidiradi → ~5ms
   TOPILMADI        → 404 Not Found
   Muddati o'tgan   → 410 Gone
   TOPILDI          → Redis ga kesh → 302 redirect ✅
```

Ikkinchi so'rovdan boshlab Redis dan keladi — DB ga tegmaydi.

---

### `backend/app/main.py`
FastAPI application entry point.

```
Server yonganda (lifespan):
  → PostgreSQL da urls jadvali yo'q bo'lsa yaratadi (create_all)
  → CORS middleware yoqiladi (frontend so'rovlari uchun)
  → /api/v1 → shorten router
  → /       → redirect router
  → /health → {"status": "ok"}

Server o'chganda:
  → Redis ulanishni yopadi
  → PostgreSQL pool ni yopadi
```

> **Eslatma:** `create_all` faqat jadval yo'q bo'lsa yaratadi. Alembic o'rnatilgach bu qator olib tashlanadi.

---

## Alembic migratsiya

### Nima uchun Alembic?

| | `create_all` | Alembic |
|--|--|--|
| Jadval yo'q bo'lsa | Yaratadi | Yaratadi |
| Jadval o'zgarsa | Hech narsa qilmaydi ❌ | O'zgarishni qo'llaydi ✅ |
| Tarix | Yo'q | Har versiya saqlanadi |
| Rollback | Yo'q | `downgrade` bilan qaytarish mumkin |

### Muammo va yechim

**Muammo 1 — Async driver:**
Alembic standart `env.py` sync ishlaydi, `asyncpg` esa async. 
Yechim: `asyncio.run()` + `create_async_engine` qo'shildi.

**Muammo 2 — .env topilmadi:**
Alembic `poc014-app/` dan ishga tushadi, `.env` esa `backend/` da.
Yechim: `load_dotenv(BACKEND_DIR + '/.env')` qo'shildi.

**Muammo 3 — Bo'sh migration:**
`create_all` jadval yaratib qo'ygan edi — Alembic farq topolmadi.
Yechim: `DROP TABLE urls` → qayta `autogenerate`.

### Migration fayli: `3730a3bcc47f_create_urls_table.py`

```python
def upgrade():
    op.create_table('urls',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('short_code', sa.String(20), nullable=False),
        sa.Column('long_url', sa.Text(), nullable=False),
        sa.Column('is_custom', sa.Boolean(), nullable=False),
        sa.Column('click_count', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default='now()'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_urls_short_code', 'urls', ['short_code'], unique=True)

def downgrade():
    op.drop_index('ix_urls_short_code', table_name='urls')
    op.drop_table('urls')
```

### Buyruqlar

```bash
# Migration yaratish
alembic revision --autogenerate -m "create_urls_table"

# DB ga qo'llash
alembic upgrade head

# Hozirgi versiyani ko'rish
alembic current
# → 3730a3bcc47f (head)

# Orqaga qaytarish (kerak bo'lsa)
alembic downgrade -1
```

---

## Unit testlar

### `tests/test_base62.py`

```
test_encode_basic         → encode(1000000) == "4C92"       ✅
test_encode_zero          → encode(0) == "0"                ✅
test_decode_basic         → decode("4C92") == 1000000       ✅
test_encode_decode_roundtrip → har ikki tomonga ishlaydi     ✅
test_short_length         → 6 belgi yetarli                 ✅

Jami: 5/5 passed — 0.01s
```

```bash
pytest tests/test_base62.py -v
# 5 passed in 0.01s
```

---

## Frontend

**Stack:** React 18 + Vite 8 + Tailwind CSS v4

**Funksiyalar:**
- URL kiritish → `POST /api/v1/shorten` ga yuboradi
- Custom alias (ixtiyoriy)
- TTL tanlash (Doimiy / 1 / 7 / 30 kun)
- Natija ko'rsatish — qisqa URL
- Nusxalash tugmasi — clipboard ga ko'chiradi
- Xato holati — qizil banner
- Enter tugmasi bilan ham yuborish mumkin

**Proxy sozlamasi** (`vite.config.js`):
```javascript
proxy: {
  '/api': 'http://localhost:8000',
  '/health': 'http://localhost:8000',
}
```
Frontend `localhost:5173` da, backend `localhost:8000` da — proxy CORS muammosini hal qiladi.

---

## Definition of Done — tekshiruv

| Mezon | Natija |
|-------|--------|
| `curl POST /api/v1/shorten` ishlaydi | ✅ |
| Brauzerda redirect ishlaydi | ✅ |
| Redis kesh ishlaydi | ✅ `redis-cli GET "url:4C92"` → URL qaytaradi |

---

## Qo'lda test

```bash
# 1. URL qisqartirish
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url": "https://uzinfocom.uz/projects/..."}'

# Javob:
# {"short_url":"http://localhost:8000/4C92","short_code":"4C92",...}

# 2. Redis da borligini tekshirish
redis-cli GET "url:4C92"
# → "https://uzinfocom.uz/projects/..."

# 3. DB da borligini tekshirish
psql -U poc014user -d poc014 -h localhost \
  -c "SELECT id, short_code, long_url, created_at FROM urls;"

# 4. Health check
curl http://localhost:8000/health
# → {"status":"ok","service":"poc014-url-shortener"}
```

---

## Serverni ishga tushirish

```bash
# Backend
cd ~/POC/poc014-app/backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (yangi terminal)
cd ~/POC/poc014-app/frontend
npm run dev
# → http://localhost:5173

# Swagger UI
# → http://localhost:8000/docs
```

---

## Navbatdagi qadam — Sprint 2

- ClickHouse o'rnatish (analytics uchun)
- Click event logger
- `GET /api/v1/stats/{code}`
- Rate limiting
- QR code generator (frontend)

---

*POC-014 · Uzinfocom R&D · Sprint 1 · Aprel 2026*