# POC-014 Sprint 4 — Prometheus va Error Handling

**Muallif:** Rovshen R. Ashirov  
**Loyiha:** POC-014 URL Shortener  
**Sana:** May 2026  
**Holat:** ✅ Tugallandi

---

## Maqsad

Sprint 4 da quyidagilar bajarildi:
- Prometheus metrics endpoint
- `/api/v1/metrics/summary` — o'qish oson endpoint
- Error handling tekshiruvi

---

## Bajarilgan ishlar

| # | Vazifa | Holat |
|---|--------|-------|
| 1 | Prometheus metrics `/metrics` | ✅ |
| 2 | `/api/v1/metrics/summary` | ✅ |
| 3 | Error handling tekshiruvi | ✅ |
| 4 | Load test | ✅ (alohida hujjat) |

---

## 1. Prometheus metrics

### Prometheus nima?

Prometheus — serverning ichki holatini kuzatib boruvchi monitoring tizimi.

**Oddiy misol:**
```
Mashina dashboard:
  Tezlik:   120 km/h
  Yoqilg'i: 40%
  Harorat:  90°C

Prometheus ham shunday:
  RPS:      5,298
  RAM:      83MB
  CPU:      45%
  Xatolar:  0
```

**Qanday ishlaydi:**
```
FastAPI server → /metrics endpoint (matn ko'rinishida)
      ↓
Prometheus server → har 15 soniyada /metrics ni o'qiydi
      ↓
Grafana → chiroyli grafik ko'rsatadi
```

**Nima uchun kerak:**
```
Load test paytida:
  RPS qancha?      → Prometheus ko'rsatadi
  Xato ko'paydimi? → Prometheus ogohlantiradi
  RAM oshyaptimi?  → Prometheus ko'rsatadi

Production da muammo chiqqanda:
  Qachon boshlandi? → Prometheus tarixdan ko'rsatadi
```

### O'rnatish

```bash
pip install prometheus-fastapi-instrumentator
```

### `main.py` ga qo'shish

```python
from prometheus_fastapi_instrumentator import Instrumentator

# app yaratilgandan keyin
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=False,
).instrument(app).expose(app)
```

Bu ikki qator:
```
instrument(app) → barcha so'rovlarni kuzata boshlaydi
expose(app)     → /metrics endpoint yaratadi
```

### `/metrics` endpoint

```bash
curl http://localhost:8000/metrics
```

**Natija (asosiy ko'rsatkichlar):**
```
# Python holati
python_gc_objects_collected_total{generation="0"} 410.0
python_gc_objects_collected_total{generation="1"} 79.0

# Xotira
process_resident_memory_bytes 8.67e+07   → 87MB

# CPU
process_cpu_seconds_total 0.78

# HTTP so'rovlar
http_requests_total{handler="/{short_code}", method="GET", status="3xx"} 3.0
http_requests_total{handler="/metrics", method="GET", status="2xx"} 1.0

# Latency histogram
http_request_duration_highr_seconds_bucket{le="0.01"} 0.0
http_request_duration_highr_seconds_bucket{le="0.025"} 0.0
...
```

**Muammo:** `/metrics` matn ko'rinishida — o'qish qiyin.  
**Yechim:** `/api/v1/metrics/summary` endpoint yaratildi.

---

## 2. `/api/v1/metrics/summary` endpoint

**Fayl:** `backend/app/api/v1/metrics_view.py`

```python
from fastapi import APIRouter
from prometheus_client import REGISTRY

router = APIRouter()

@router.get("/metrics/summary")
async def metrics_summary():
    metrics = {}
    total_requests = 0

    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == "http_requests_total":
                total_requests += sample.value  # barcha labellarni yig'amiz
            else:
                metrics[sample.name] = sample.value

    return {
        "memory_mb": round(metrics.get("process_resident_memory_bytes", 0) / 1024 / 1024, 2),
        "cpu_seconds": round(metrics.get("process_cpu_seconds_total", 0), 2),
        "total_requests": int(total_requests),
        "open_files": metrics.get("process_open_fds", 0),
    }
```

**Nima uchun `total_requests` yig'amiz:**
```
Prometheus da http_requests_total bir nechta label bilan saqlanadi:
  http_requests_total{handler="/{short_code}", status="3xx"} = 2
  http_requests_total{handler="/api/v1/shorten", status="2xx"} = 1

metrics.get() faqat birini oladi → noto'g'ri
Yig'ish → barcha endpointlar hisoblanadi → to'g'ri
```

**`main.py` ga router qo'shish:**
```python
from app.api.v1 import shorten, redirect, stats, analytics, metrics_view

app.include_router(metrics_view.router, prefix="/api/v1")
```

### Test natijalari

```bash
# Boshlang'ich holat
curl http://localhost:8000/api/v1/metrics/summary
# → {"memory_mb": 82.31, "cpu_seconds": 0.78, "total_requests": 0, "open_files": 23}

# 2 ta redirect yuborildi
curl http://localhost:8000/4C92
curl http://localhost:8000/4C92

# Tekshiramiz
curl http://localhost:8000/api/v1/metrics/summary
# → {"memory_mb": 83.01, "cpu_seconds": 0.62, "total_requests": 2, "open_files": 24}

# Yana 1 ta redirect
curl http://localhost:8000/4C92

# Tekshiramiz
curl http://localhost:8000/api/v1/metrics/summary
# → {"memory_mb": 83.01, "cpu_seconds": 0.65, "total_requests": 3, "open_files": 24}
```

**Muhim:** `/metrics/summary` o'zi hisoblanmaydi — faqat haqiqiy so'rovlar.

### Javob formati

```json
{
  "memory_mb": 83.01,
  "cpu_seconds": 0.65,
  "total_requests": 3,
  "open_files": 24
}
```

| Maydon | Ma'no |
|--------|-------|
| `memory_mb` | Server ishlatayotgan RAM (MB) |
| `cpu_seconds` | Server yongandan beri CPU ishlatishi (soniya) |
| `total_requests` | Jami qayta ishlangan so'rovlar |
| `open_files` | Ochiq fayl va socketlar soni |

---

## 3. Error handling tekshiruvi

Barcha xato holatlari `HTTPException` orqali qaytariladi — alohida middleware shart emas.

### 400 — Noto'g'ri URL format

```bash
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url": "not-a-url"}'
```

```json
HTTP/1.1 400 Bad Request
{"detail": "Noto'g'ri URL format"}
```

**Qaerda tekshiriladi:** `shorten.py`
```python
if not validators.url(req.long_url):
    raise HTTPException(status_code=400, detail="Noto'g'ri URL format")
```

---

### 404 — URL topilmadi

```bash
curl http://localhost:8000/notexist
```

```json
HTTP/1.1 404 Not Found
{"detail": "URL topilmadi"}
```

**Qaerda tekshiriladi:** `redirect.py`
```python
if not url:
    raise HTTPException(status_code=404, detail="URL topilmadi")
```

---

### 409 — Alias band

```bash
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url": "https://uzinfocom.uz", "alias": "mavjud-alias"}'
```

```json
HTTP/1.1 409 Conflict
{"detail": "Bu alias band"}
```

---

### 410 — URL muddati o'tgan

```bash
# Redis dan o'chirildi → PostgreSQL dan tekshirildi → muddati o'tgan
redis-cli DEL "url:rovshen"
curl -v http://localhost:8000/rovshen
```

```
HTTP/1.1 410 Gone
{"detail": "URL muddati o'tgan"}
```

**Muhim kashfiyot:**
```
DB da muddatni o'zgartirdik
Lekin Redis da kesh bor edi → 302 redirect qaytardi ❌

Redis dan o'chirgach → PostgreSQL dan o'qidi
expires_at tekshirildi → 410 Gone ✅

Xulosa: DB ni o'zgartirganda Redis keshni ham tozalash kerak
```

**Qaerda tekshiriladi:** `redirect.py`
```python
if url.expires_at and url.expires_at < datetime.now(timezone.utc):
    raise HTTPException(status_code=410, detail="URL muddati o'tgan")
```

---

### 429 — Rate limit

```bash
# 100 dan ortiq so'rov yuborganda
HTTP/1.1 429 Too Many Requests
{"detail": "Limitdan oshdingiz. 3548 soniyadan keyin urinib ko'ring"}
```

**Qaerda tekshiriladi:** `rate_limit.py`
```python
if count > 100:
    remaining = await redis.ttl(key)
    raise HTTPException(
        status_code=429,
        detail=f"Limitdan oshdingiz. {remaining} soniyadan keyin urinib ko'ring"
    )
```

---

## Xato holatlari jadvali

| Kod | Holat | Sabab | Qaerda |
|-----|-------|-------|--------|
| 400 | Bad Request | Noto'g'ri URL format | `shorten.py` |
| 404 | Not Found | URL topilmadi | `redirect.py` |
| 409 | Conflict | Alias band | `shorten.py` |
| 410 | Gone | Muddati o'tgan | `redirect.py` |
| 429 | Too Many Requests | Rate limit | `rate_limit.py` |
| 422 | Unprocessable Entity | So'rov formati noto'g'ri | FastAPI auto |

---

## Definition of Done

| Mezon | Natija |
|-------|--------|
| `/metrics` endpoint ishlaydi | ✅ |
| `/api/v1/metrics/summary` ishlaydi | ✅ |
| total_requests to'g'ri hisoblanadi | ✅ |
| 400 xato ishlaydi | ✅ |
| 404 xato ishlaydi | ✅ |
| 410 xato ishlaydi | ✅ |
| 429 xato ishlaydi | ✅ |

---

*POC-014 · Uzinfocom R&D · Sprint 4 · May 2026*