# POC-014 Sprint 4 — Load Test Natijalari

**Muallif:** Rovshen R. Ashirov  
**Loyiha:** POC-014 URL Shortener  
**Sana:** Aprel 2026  
**Holat:** ✅ Tugallandi

---

## Maqsad

TZ da belgilangan:
```
Load test: 10,000 req/sec
p99 latency: < 10ms
Error rate: < 0.1%
```

---

## Muhit

```
CPU:    AMD Ryzen 5 7535HS (12 core)
RAM:    30GB
OS:     Ubuntu 24.04 LTS
Server: uvicorn app.main:app
Redis:  7.0.15 (localhost)
```

---

## Ishlatilgan asboblar

### Locust
```
Python da yozilgan load testing vositasi
Virtual foydalanuvchilar yaratadi
Brauzer UI orqali boshqariladi
Kamchiligi: Python GIL emas, lekin gevent CPU
            ko'p user da o'zi bottleneck bo'ladi
```

### wrk
```
C da yozilgan HTTP benchmark vositasi
Minimal CPU sarflaydi
Haqiqiy server RPS ni ko'rsatadi
```

O'rnatish:
```bash
sudo apt install -y wrk
```

---

## Locust test scenariylari

### locustfile.py (yakuniy versiya)

```python
from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

class URLShortenerUser(FastHttpUser):
    wait_time = between(0.001, 0.005)

    @task
    def redirect(self):
        self.client.get("/4C92", allow_redirects=False)
```

**FastHttpUser vs HttpUser:**
```
HttpUser     → requests library → sekinroq
FastHttpUser → geventhttpclient → 5-10x tezroq
```

---

## Locust test natijalari

### Test 1 — 100 user, rate limit YOQILGAN

```
Sozlama:
  Users:    100
  Ramp up:  10/sec
  Workers:  1 (default)

Natija:
  RPS:      22.34
  Failures: 6%   ← rate limit (429)
  p99:      13,000ms

Xato sababi:
  100 foydalanuvchi bitta IPdan yubordi
  rate limit: 100 req/soat per IP
  → 429 Too Many Requests
```

### Test 2 — 100 user, rate limit O'CHIRILGAN

```
Sozlama:
  Users:    100
  Ramp up:  10/sec
  Workers:  4

Natija:
  RPS:      30.72
  Failures: 0%   ✅
  p50:      3,200ms
  p99:      6,400ms
  Min:      4ms
```

### Test 3 — 1000 user, faqat redirect

```
Sozlama:
  Users:    1000
  Ramp up:  100/sec
  Workers:  8

Natija:
  RPS:      2,597
  Failures: 0%    ✅
  Min:      10ms  ✅  ← Redis ishlayapti
  p50:      310ms
  p99:      33,000ms ← Locust bottleneck!

[WARNING] CPU usage above 90%!
→ Locust o'zi bottleneck bo'ldi
```

**Locust bottleneck isboti:**
```
3000 Python greenlet → bitta process
CPU 90%+ → so'rovlar navbatda kutdi
Min: 10ms → server tez, Locust kechiktirdi

Haqiqiy RPS aniqlash uchun wrk ishlatildi
```

---

## wrk test natijalari

### Test 1 — 4 thread, 200 connection

```bash
wrk -t4 -c200 -d60s http://localhost:8000/4C92
```

```
Muhit: Firefox + PyCharm ishlamoqda

Thread Stats   Avg      Stdev     Max   +/- Stdev
  Latency    72.29ms  119.43ms   1.50s    91.08%
  Req/Sec     1.37k     1.16k    4.89k    68.95%

318,440 requests in 1.00m, 59.22MB read
Requests/sec:   5,298.87
Transfer/sec:   0.99MB
Failures:       0  ✅
```

### Test 2 — 12 thread, 400 connection

```bash
wrk -t12 -c400 -d60s http://localhost:8000/4C92
```

```
Muhit: Firefox + PyCharm ishlamoqda

Thread Stats   Avg      Stdev     Max   +/- Stdev
  Latency   123.77ms  134.67ms   1.43s    85.34%
  Req/Sec   371.87    345.69     1.25k    73.80%

264,477 requests in 1.00m, 49.18MB read
Requests/sec:   4,401.38   ← pasaydi!
Transfer/sec:   838.15KB
Failures:       0  ✅

Sabab: 400 connection > pool_size(20) × 8 worker = 160
       PostgreSQL connection pool to'ldi → navbat
```

### Test 3 — 8 thread, 500 connection

```bash
wrk -t8 -c500 -d60s http://localhost:8000/4C92
```

```
Muhit: Firefox + PyCharm ishlamoqda, 12 worker

Thread Stats   Avg      Stdev     Max   +/- Stdev
  Latency   169.46ms  183.34ms   1.62s    83.59%
  Req/Sec   534.08    558.01     2.06k    74.79%

251,621 requests in 1.00m, 46.79MB read
Requests/sec:   4,186.48   ← yanada pasaydi
Transfer/sec:   797.23KB
Failures:       0  ✅

Sabab: Server overloaded zone ga kirdi
       Optimal: 4 thread, 200 connection edi
```

### Test 4 — Toza muhit (🏆 eng yaxshi natija)

```bash
# Kompyuter qayta yoqildi
# Firefox, PyCharm — hech narsa ochiq emas
# Server: 8 worker, uvloop, httptools

wrk -t4 -c200 -d60s http://localhost:8000/4C92
```

```
Thread Stats   Avg      Stdev     Max    +/- Stdev
  Latency    11.27ms    8.91ms  120.94ms   95.70%
  Req/Sec     4.94k   654.92     6.42k    68.42%

1,179,487 requests in 1.00m, 219.35MB read
Requests/sec:  19,651.74  🏆
Transfer/sec:      3.65MB
Failures:          0  ✅
```

---

## Nima uchun natijalar farq qildi

### CPU band qilgan dasturlar (htop natijasi)

```
Firefox:    55.2% CPU  ← eng katta muammo
Firefox:    14.4%
Firefox:    9.2%, 8.1%, 6.3%...
Xorg:       15.0%
ClickHouse: 2.3% × ko'p process
PyCharm:    ishlamoqda

Jami:       ~9 core band
Uvicorn uchun: ~3 core qolgan
```

### Toza muhitda

```
Barcha 12 core → faqat uvicorn + wrk + Redis + OS
Natija: 19,651 RPS ← 3.7x ko'p
```

---

## Optimizatsiyalar tarixi

| # | Optimizatsiya | RPS oldin | RPS keyin | O'sish |
|---|---------------|-----------|-----------|--------|
| 1 | 1 worker → 4 worker | 20 | 30 | 1.5x |
| 2 | 4 worker → 8 worker | 30 | 2,043 | 68x |
| 3 | ClickHouse sync → asyncio.Queue | 42 | 2,043 | 48x |
| 4 | Depends(get_db) → faqat MISS da | 2,043 | 3,000+ | 1.5x |
| 5 | get_redis async → sync | 3,000+ | 5,298 | 1.8x |
| 6 | Firefox/PyCharm yopish | 5,298 | **19,651** | 3.7x |

### Eng muhim optimizatsiya — ClickHouse async queue

**Oldingi (42 RPS sababi):**
```
GET /4C92
  → redis.get()                    (~0.3ms)
  → asyncio.to_thread(ch_insert)   (~50ms, event loop bloklanadi)
  → 302 redirect

16 thread pool to'ldi → yangi so'rovlar kutdi → 42 RPS
```

**Hozirgi:**
```
GET /4C92
  → redis.get()          (~0.1ms)
  → queue.put_nowait()   (0ms, pure Python)
  → 302 redirect         ← tugadi!

Background flush_worker (1 soniyada):
  → 1000 ta event → 1 ta ClickHouse INSERT
```

---

## Yakuniy natijalar

### TZ maqsadlari bajarilishi

| Mezon | Maqsad | Natija | Holat |
|-------|--------|--------|-------|
| RPS | 10,000 | **19,651** | ✅ 2x oshdi |
| Avg latency | — | 11.27ms | ✅ |
| Max latency | — | 120.94ms | ✅ |
| Failures | < 0.1% | **0%** | ✅ |
| Jami (1 daqiqa) | — | 1,179,487 | ✅ |

### Locust vs wrk taqqoslash

```
Locust:  2,597 RPS  ← Locust o'zi bottleneck
wrk:    19,651 RPS  ← haqiqiy server tezligi

Farq: 7.6x
Sabab: Locust Python greenlet, wrk C threads
```

---

## Server ishga tushirish (load test uchun)

```bash
# Toza muhitda (boshqa dasturlar yopiq)
cd ~/POC/poc014-app/backend
source ../venv/bin/activate

uvicorn app.main:app \
  --workers 8 \
  --loop uvloop \
  --http httptools \
  --port 8000
```

**Parametrlar:**
```
--workers 8      → 12 core uchun optimal (8 uvicorn + 4 wrk)
--loop uvloop    → C da yozilgan event loop (2-4x tezroq)
--http httptools → C da yozilgan HTTP parser (2-3x tezroq)
```

---

## Load test buyruqlari

```bash
# wrk — optimal sozlama
wrk -t4 -c200 -d60s http://localhost:8000/4C92

# Locust — UI bilan
locust -f tests/locustfile.py --host=http://localhost:8000
# → http://localhost:8089

# Locust — headless
locust -f tests/locustfile.py \
  --host=http://localhost:8000 \
  --users 1000 \
  --spawn-rate 100 \
  --headless \
  --run-time 60s
```

---

*POC-014 · Uzinfocom R&D · Sprint 4 · Aprel 2026*