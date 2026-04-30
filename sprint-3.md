# POC-014 Sprint 3 — Analytics Dashboard

**Muallif:** Rovshen R. Ashirov  
**Loyiha:** POC-014 URL Shortener  
**Sana:** Aprel 2026  
**Holat:** ✅ Tugallandi

---

## Maqsad

Sprint 2 da click ma'lumotlari ClickHouse ga yozilgan edi. Sprint 3 da:
- Bu ma'lumotlarni o'qib API orqali chiqarish
- Real-time WebSocket
- Frontend dashboard — grafik, geo, referrer
- Links ro'yxati UI

---

## Bajarilgan ishlar

| # | Vazifa | Holat |
|---|--------|-------|
| 1 | GET /api/v1/analytics/{code}/timeseries | ✅ |
| 2 | GET /api/v1/analytics/{code}/geo | ✅ |
| 3 | GET /api/v1/analytics/{code}/referrers | ✅ |
| 4 | WebSocket /ws/stats/{code} | ✅ |
| 5 | Chart.js — timeseries grafik | ✅ |
| 6 | Geo bar chart | ✅ |
| 7 | Referrer bar chart | ✅ |
| 8 | Links ro'yxati UI | ✅ |

---

## 1. Analytics endpointlar

**Fayl:** `backend/app/api/v1/analytics.py`

### Nima uchun 3 ta alohida endpoint?

```
Har endpoint — alohida ma'lumot turi:

timeseries → vaqt bo'yicha grafik uchun
geo        → geografik taqsimlash uchun
referrers  → qayerdan kelishdi uchun

Alohida bo'lsa:
  Frontend faqat kerakligini so'raydi
  ClickHouse faqat kerakli so'rovni bajaradi
```

---

### 1.1 Timeseries endpoint

```python
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
```

**ClickHouse so'rovi tushuntirish:**
```
toDate(event_time)     → timestamp → sana (2026-04-30)
COUNT(*)               → o'sha kunda nechta click
GROUP BY date          → har kun alohida hisoblaydi
ORDER BY date ASC      → eski → yangi tartib
INTERVAL 7 DAY         → faqat so'nggi 7 kun

Natija:
  2026-04-24 → 142
  2026-04-25 → 238
  2026-04-30 → 156
```

**Test natijasi:**
```json
GET /api/v1/analytics/4C92/timeseries

[
  { "date": "2026-04-30", "clicks": 1 }
]
```

---

### 1.2 Geo endpoint

```python
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
```

**`SUM(COUNT(*)) OVER()` nima:**
```
Window function — barcha guruhlar yig'indisi

UZ → 820 click
RU → 310 click
KZ → 120 click
Jami → 1250

UZ foizi = 820 / 1250 * 100 = 65.6%
RU foizi = 310 / 1250 * 100 = 24.8%

OVER() = barcha qatorlar bo'yicha hisoblaydi
```

**Test natijasi:**
```json
GET /api/v1/analytics/4C92/geo

[
  { "country_code": "UZ", "clicks": 1, "pct": 100.0 }
]
```

---

### 1.3 Referrers endpoint

```python
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
```

**Test natijasi:**
```json
GET /api/v1/analytics/4C92/referrers

[
  { "domain": "direct", "clicks": 1, "pct": 50.0 },
  { "domain": "127.0.0.1:8000", "clicks": 1, "pct": 50.0 }
]
```

---

## 2. WebSocket endpoint

**Fayl:** `backend/app/main.py`

```python
@app.websocket("/ws/stats/{short_code}")
async def websocket_stats(websocket: WebSocket, short_code: str):
    await websocket.accept()
    try:
        while True:
            client = get_clickhouse()

            total = client.query(f"""
                SELECT COUNT(*) FROM {settings.CLICKHOUSE_DB}.click_events
                WHERE short_code = '{short_code}'
            """)

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

            await asyncio.sleep(5)
    except Exception:
        await websocket.close()
```

### Qanday ishlaydi

```
Foydalanuvchi dashboard ni ochdi
    ↓
WebSocket ulanish ochildi (ws://localhost:8000/ws/stats/4C92)
    ↓
while True:
  ClickHouse → total_clicks, today_clicks o'qidi
  Foydalanuvchiga yubordi
  5 soniya kutdi
  Qaytadan...
    ↓
Foydalanuvchi sahifani yopdi
    ↓
Exception → websocket.close()
```

### HTTP va WebSocket farqi

```
HTTP:
  Foydalanuvchi → so'rov → Server → javob → TUGADI
  Yangi ma'lumot kerak → yana so'rov kerak

WebSocket:
  Foydalanuvchi → ulanish → DOIM OCHIQ
  Server → 5 soniyada bir → ma'lumot yuboradi
  Foydalanuvchi so'ramasdan ham oladi ✅
```

### Nima uchun Swagger da ko'rinmaydi

```
Swagger UI → faqat HTTP endpointlarni ko'rsatadi
WebSocket  → Swagger da ko'rinmaydi ❌

Test usuli → brauzer console:
  const ws = new WebSocket('ws://localhost:8000/ws/stats/4C92')
  ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

---

## 3. Links API endpoint

**Fayl:** `backend/app/api/v1/shorten.py`

```python
@router.get("/links", response_model=list[LinkItem])
async def get_links(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(URL).order_by(URL.created_at.desc()).limit(20)
    )
    urls = result.scalars().all()
    return [
        LinkItem(
            short_code=u.short_code,
            short_url=f"{settings.BASE_URL}/{u.short_code}",
            long_url=u.long_url,
            click_count=u.click_count,
            created_at=u.created_at,
            expires_at=u.expires_at,
            is_custom=u.is_custom,
        )
        for u in urls
    ]
```

**Tushuntirish:**
```
order_by(URL.created_at.desc()) → eng yangi birinchi
limit(20)                       → maksimal 20 ta
result.scalars().all()          → barcha qatorlarni list ga aylantiradi
```

---

## 4. Frontend — Dashboard.jsx

**Fayl:** `frontend/src/Dashboard.jsx`

### Tuzilmasi

```
Dashboard komponenti:
  ├── WebSocket — real-time stats (total, today)
  ├── HTTP fetch — timeseries, geo, referrers (bir marta)
  ├── Metric cards — total_clicks, today_clicks
  ├── Chart.js — timeseries grafik
  ├── Geo bar chart
  └── Referrer bar chart
```

### WebSocket ulanish

```javascript
useEffect(() => {
    if (!shortCode) return
    const ws = new WebSocket(`ws://localhost:8000/ws/stats/${shortCode}`)
    ws.onmessage = (e) => setStats(JSON.parse(e.data))
    return () => ws.close()  // Komponent o'chganda WebSocket yopiladi
}, [shortCode])
```

**`return () => ws.close()` nima:**
```
useEffect cleanup function
Foydalanuvchi boshqa sahifaga o'tsa → ws.close() chaqiriladi
WebSocket ortiqcha ochiq qolmaydi
Server resurslarini bo'shatadi
```

### Analytics ma'lumotlarini olish

```javascript
useEffect(() => {
    if (!shortCode) return

    fetch(`/api/v1/analytics/${shortCode}/timeseries`)
        .then(r => r.json()).then(setTimeseries)

    fetch(`/api/v1/analytics/${shortCode}/geo`)
        .then(r => r.json()).then(setGeo)

    fetch(`/api/v1/analytics/${shortCode}/referrers`)
        .then(r => r.json()).then(setReferrers)
}, [shortCode])   // shortCode o'zgarganda qayta yuklanadi
```

**Nima uchun WebSocket emas HTTP:**
```
timeseries, geo, referrers → sekin o'zgaradigan ma'lumot
  Har 5 soniyada ClickHouse ga 3 ta so'rov → keraksiz yuk

total_clicks, today_clicks → tez o'zgaradigan ma'lumot
  WebSocket bilan yetarli ✅
```

### Chart.js grafik

```javascript
useEffect(() => {
    if (!timeseries.length || !chartRef.current) return

    if (chartInstance.current) chartInstance.current.destroy()

    chartInstance.current = new Chart(chartRef.current, {
        type: 'line',
        data: {
            labels: timeseries.map(t => t.date),
            datasets: [{
                label: 'Clicklar',
                data: timeseries.map(t => t.clicks),
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37,99,235,0.08)',
                fill: true,
                tension: 0.4,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true }
            }
        }
    })
}, [timeseries])
```

**`chartInstance.current.destroy()` nima uchun:**
```
timeseries yangilansa → yangi Chart yaratiladi
Eski Chart o'chirilmasa → ikkita Chart bir canvas da → xato ❌
destroy() → eski chartni o'chiradi → yangi yaratiladi ✅
```

---

## 5. Frontend — LinksList.jsx

**Fayl:** `frontend/src/LinksList.jsx`

```javascript
export default function LinksList({ onSelect }) {
    const [links, setLinks] = useState([])

    useEffect(() => {
        fetch('/api/v1/links')
            .then(r => r.json())
            .then(setLinks)
    }, [])   // [] = faqat bir marta, sahifa yuklanganida

    return (
        // Har link bosilganda → onSelect(link) chaqiriladi
        // App.jsx da: onSelect={(link) => setResult(link)}
        // → Dashboard yangi link uchun ochiladi
    )
}
```

**Badge lar:**
```
is_custom = true  → "custom" — binafsha badge
expires_at bor    → sana — sariq badge
```

---

## Umumiy oqim — Sprint 3 da

```
Foydalanuvchi URL qisqartirdi
    ↓
result set bo'ldi → Dashboard ochildi
    ↓
Parallel:
  WebSocket ulanish ochildi → 5 soniyada bir:
    total_clicks, today_clicks yangilanadi 🟢

  HTTP fetch:
    timeseries → Chart.js grafik
    geo        → bar chart (UZ 100%)
    referrers  → bar chart (direct 50%, 127.0.0.1 50%)
    ↓
Dashboard ko'rsatildi ✅

Links ro'yxati:
  Sahifa yuklanganida → GET /api/v1/links
  4 ta link ko'rsatildi
  Bosilsa → o'sha link uchun Dashboard ochiladi
```

---

## Definition of Done

| Mezon | Natija |
|-------|--------|
| timeseries endpoint | ✅ |
| geo endpoint | ✅ |
| referrers endpoint | ✅ |
| WebSocket 5s yangilanish | ✅ |
| Chart.js grafik | ✅ |
| Geo bar chart | ✅ |
| Referrer bar chart | ✅ |
| Links ro'yxati | ✅ |

---

## Navbatdagi qadam — Sprint 4

- Locust load test — 10K req/sec
- Prometheus metrics
- Error handling yaxshilash
- README.md

---

*POC-014 · Uzinfocom R&D · Sprint 3 · Aprel 2026*