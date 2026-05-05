
# POC-014 - URL Shortener с аналитикой - Mini bit.ly
# Asosiy Tushunchalar

**Muallif:** Rovshen R. Ashirov  
**Loyiha:** POC-014 URL Shortener  
**Sana:** Aprel 2026

---

## 1. URL Shortener nima va nima uchun kerak?

URL Shortener — uzun havolalarni qisqa, eslab qolish oson bo'lgan formatga aylantiradigan servis.

**Oddiy misol:**
```
Uzun:  https://uzinfocom.uz/projects/pravitelstvennyi-portal-respubliki-uzbekistan-gov-uz-ru-42
Qisqa: http://localhost:8000/4C92
```

**Nima uchun kerak:**
- **SMS da** — SMS 160 belgi bilan cheklangan, uzun URL joy olmaydi
- **QR kodda** — uzun URL = katta, murakkab QR kod; qisqa URL = kichik, toza QR kod
- **Analytika uchun** — nechta odam bosganini, qaysi davlatdan ekanini bilsa bo'ladi
- **Vaqtinchalik havolalar** — muddati o'tgach avtomatik o'chadi

**Uzinfocom uchun:**
- Gosportallar (my.gov.uz, egov.uz) da uzun API URLlarni qisqartirish
- UTM-analytika orqali marketing kampaniyalar samaradorligini o'lchash
- QR kod — davlat hujjatlarida, bilboradlarda

---

## 2. ID Generatsiya algoritmlari

Har bir yangi URL uchun noyob qisqa kod yaratish usullari.

### Base62 ✅ (biz ishlatdik)
```
Belgilar: 0-9, A-Z, a-z  (62 ta)

encode(1000001) → "4C93"
encode(1000002) → "4C94"
```
- **Afzalligi:** Eng qisqa (6 belgi), tez, URL uchun xavfsiz (+ / yo'q)
- **Kamchiligi:** Ketma-ket — taxmin qilish mumkin
- **Ishlatadi:** bit.ly, TinyURL

### UUID v4
```
128-bit random son
a3f2b1c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c  (36 belgi)
```
- **Afzalligi:** Hech kim taxmin qila olmaydi
- **Kamchiligi:** 36 belgi — URL uchun juda uzun ❌

### Snowflake ID (Twitter ixtiro qilgan)
```
64 bit = Timestamp(41) + Mashina(10) + Ketma-ket(12)
1823456789012345678 → "aB3xK9" (10 belgi)
```
- **Afzalligi:** Ko'p server parallel ishlasa ham noyob, vaqt bo'yicha tartiblangan
- **Kamchiligi:** Base62 dan uzunroq, sozlash murakkab
- **Ishlatadi:** Twitter, Discord, Instagram

### NanoID
```
secrets.token_urlsafe(6) → "aB3xK9"
Kriptografik tasodifiy
```
- **Afzalligi:** Xavfsiz, taxmin qilib bo'lmaydi, library shart emas
- **Kamchiligi:** DB da bor-yo'qligini tekshirish kerak

### Taqqoslash

| Algoritm | Uzunlik | Xavfsiz | Murakkablik |
|----------|---------|---------|-------------|
| Base62 | 6 belgi ✅ | O'rta | Oddiy ✅ |
| UUID | 36 belgi ❌ | Yuqori | Oddiy |
| Snowflake | 10 belgi | Yuqori | Murakkab |
| NanoID | 8 belgi | Yuqori | Oddiy ✅ |

---

## 3. Base62 nima?

Raqamlarni qisqa kodga aylantiradigan hisoblash sistemasi.

```
Oddiy sanoqda 10 ta belgi: 0 1 2 3 4 5 6 7 8 9
Base62 da 62 ta belgi:
  0-9, A-Z, a-z

1000000 → "4C92"   (4 belgi!)
1000001 → "4C93"
9999999 → "FXsj"
```

**Nima uchun Base64 emas:**
```
Base64: + / = belgilari bor → URL da muammo
Base62: faqat harf va raqam → URL da xavfsiz
```

**Bizning loyihada:**
```
PostgreSQL id = 1000001
      ↓
   Base62
      ↓
  "4C93"
      ↓
http://localhost:8000/4C93
```

---

## 4. UUID v4 nima?

Kompyuter tomonidan tasodifiy yaratilgan, dunyoda noyob identifikator.

```
Ko'rinishi: a3f2b1c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c
128 ta bit tasodifiy tanlanadi
"v4" = versiya 4, to'liq tasodifiy
```

**Noyoblik:**
```
Bir kunda 1 milliard UUID yaratilsa →
duplicate bo'lish ehtimoli → 0.00000000001%
```

**Qayerda ishlatiladi:**
- Database primary key
- Session token
- Bank tranzaksiya ID

---

## 5. Snowflake ID nima?

Twitter 2010 yilda ixtiro qilgan, vaqt asosida noyob ID yaratish usuli.

```
64 bit tarkibi:
┌─┬───────────────────────┬──────────┬────────────┐
│0│      Timestamp        │ Mashina  │  Ketma-ket │
│ │      (41 bit)         │ (10 bit) │  (12 bit)  │
└─┴───────────────────────┴──────────┴────────────┘
```

**Afzalligi:**
- Tartiblangan — katta ID = keyinroq yaratilgan
- Ko'p server — 1024 ta server parallel ishlashi mumkin
- DB ga so'rovsiz yaratiladi

**Kimlar ishlatadi:** Twitter, Discord, Instagram

---

## 6. NanoID nima?

Kriptografik tasodifiy, qisqa va xavfsiz ID yaratuvchi algoritm.

```python
import secrets
secrets.token_urlsafe(6)  → "aB3xK9"
# Library o'rnatish shart emas — Python da o'zi bor
```

**Base62 bilan farqi:**
```
Base62:  ketma-ket  → 4C93, 4C94, 4C95... (taxmin mumkin)
NanoID:  tasodifiy  → aB3xK9, mQ2Vx8...   (taxmin mumkin emas)
```

**Kamchiligi:** Yaratilgach DB da bor-yo'qligini tekshirish kerak.

---

## 7. Redis Kesh arxitekturasi

Tez-tez so'raladigan ma'lumotlarni RAM da saqlash usuli.

```
PostgreSQL → diskdan o'qiydi → 5-20ms
Redis      → RAM dan o'qiydi → 0.1-1ms
20x tezroq!
```

**Bizning loyihada:**
```
GET /4C93 keldi
      ↓
Redis da "url:4C93" bormi?
      ↓
   HA (HIT)              YO'Q (MISS)
      ↓                       ↓
  0.8ms redirect ✅      PostgreSQL → 5-20ms
                         Redis ga saqlaydi
                         redirect ✅
```

**Redis da saqlanadigan kalitlar:**
```
url:4C93        → "https://uzinfocom.uz/..."   (TTL: 24 soat)
clicks:4C93     → "42"                         (counter)
rate:192.168.1  → "45"                         (rate limit)
```

---

## 8. TTL (Time To Live) nima?

Ma'lumot qancha vaqt saqlanishini belgilaydigan muddat.

```python
redis.setex("url:4C93", 86400, "https://uzinfocom.uz/...")
#                        ↑
#                   86400 soniya = 24 soat
# 24 soat o'tgach → Redis o'zi o'chiradi
```

**Nima uchun kerak:**
```
TTL bo'lmasa → Redis RAM to'lib ketadi
TTL = 24 soat → eski, kam bosiladigan URLlar o'chadi
Ko'p bosiladigan URL → har safar yangilanadi → doim RAM da
```

---

## 9. Cache HIT va MISS nima?

- **HIT** — qidirilgan narsa keshda bor
- **MISS** — qidirilgan narsa keshda yo'q

```
1-chi so'rov  → MISS (PostgreSQL dan oladi, Redis ga saqlaydi)
2-chi so'rov  → HIT ✅
3-chi so'rov  → HIT ✅
...
1000-chi so'rov → HIT ✅

Hit rate = 99% → PostgreSQL deyarli yuklanmaydi
```

---

## 10. Cache Hit Rate nima?

Barcha so'rovlar ichida Redis dan topilgan so'rovlar foizi.

```
Hit rate = (HIT soni / Jami so'rovlar) × 100%

Misol:
  1000 ta so'rov keldi
  950 ta → Redis da topildi (HIT)
   50 ta → PostgreSQL ga tushdi (MISS)

Hit rate = 950 / 1000 × 100% = 95%
```

**Hit rate va latency:**
```
Hit rate 99% → p99 latency ~1ms   ✅
Hit rate 50% → p99 latency ~10ms  ⚠️
Hit rate 10% → p99 latency ~20ms  ❌
```

**Tekshirish:**
```bash
redis-cli INFO stats | grep hits
redis-cli INFO stats | grep misses
```

---

## 11. Click Counter nima?

Nechta odam URL ni bosganini sanash mexanizmi.

**Nima uchun Redis da:**
```
Har click da PostgreSQL UPDATE qilsa:
  1000 click → 1000 UPDATE → PostgreSQL sekinlashadi ❌

Redis bilan:
  1000 click → Redis INCR (0.01ms) ✅
  60 soniyada bir → 1 ta UPDATE ✅
```

**Oddiy misol:**
```
Kassa hisobi:
  Kun davomida → qo'l kassasida yig'adi (Redis)
  Kech soat 18:00 → bankka topshiradi (PostgreSQL)
```

---

## 12. INCR Atomic nima?

Atomic — bir operatsiya to'liq bajariladi yoki umuman bajarilmaydi.

**Muammo — atomic bo'lmasa:**
```
clicks:4C93 = 100

So'rov A: 100 ni o'qidi
So'rov B: 100 ni o'qidi
So'rov A: 100 + 1 = 101 → yozdi
So'rov B: 100 + 1 = 101 → yozdi  ← A ning natijasi yo'qoldi!

Natija: 101  ❌ (102 bo'lishi kerak edi)
```

**Redis INCR — atomic:**
```
So'rov A: 100 → 101  (to'liq bajarildi)
So'rov B: 101 → 102  (to'liq bajarildi)

Natija: 102  ✅
```

Bu **Race Condition** ni oldini oladi.

---

## 13. Click Buffer nima?

Clicklarni to'g'ridan-to'g'ri PostgreSQL ga yozmasdan, avval Redis da yig'ib, keyin bir vaqtda yozish usuli.

```
Daqiqa 1:
  /4C93 ga 500 click → Redis: clicks:4C93 = 500
  /gov-portal ga 300 click → Redis: clicks:gov-portal = 300

60 soniya o'tdi → background worker:
  PostgreSQL: click_count += 500 (4C93)
  PostgreSQL: click_count += 300 (gov-portal)
  Redis: o'chirildi

Daqiqa 2: qaytadan yig'a boshlaydi
```

**Muammo — server o'chib qolsa:**
```
Redis da 500 click bor → server o'chdi → yo'qoldi ❌
Yechim: 5 soniyada flush yoki Redis persistence (AOF)
POC uchun muhim emas, production da hal qilinadi
```

---

## 14. Rate Limiting nima?

Bir foydalanuvchi qisqa vaqt ichida juda ko'p so'rov yuborishini cheklash.

```
Qoida: 1 IP dan 1 soatda maksimal 100 so'rov

101-chi so'rovda:
  → 429 Too Many Requests
```

**Redis bilan:**
```python
count = await redis.incr(f"rate:{ip}")
if count == 1:
    await redis.expire(f"rate:{ip}", 3600)  # 1 soat
if count > 100:
    raise HTTPException(status_code=429)
```

---

## 15. Database Contention nima?

Bir vaqtda ko'p so'rov bir resursga murojaat qilganda paydo bo'ladigan "to'qnashuv."

```
Supermarket — bitta kassa:
  1 ta mijoz   → tez ✅
  10 ta mijoz  → navbat ⚠️
  100 ta mijoz → uzoq navbat ❌
```

**Bizning loyihada:**
```
1000 click bir vaqtda:
  UPDATE urls SET click_count = click_count + 1

PostgreSQL → qatorni LOCK qiladi
1-so'rov:    5ms
500-so'rov:  2500ms ❌
1000-so'rov: 5000ms ❌
```

**Yechim — Redis click buffer:**
```
1000 click → Redis INCR (lock yo'q) ✅
60 soniyada → 1 ta UPDATE → 1 ta LOCK ✅
1000x kam contention!
```

---

## 16. Analytics Pipeline — ClickHouse nima?

Click ma'lumotlarini yig'ib, qayta ishlab, dashboardga yetkazish zanjiri.

**Nima uchun PostgreSQL yetarli emas:**
```
100 million click_events:

PostgreSQL: "30 kunlik grafik?" → 30-60 soniya ❌
ClickHouse: Xuddi shu so'rov   → 0.1 soniya ✅ (300x tez!)
```

**ClickHouse — Columnar storage:**
```
PostgreSQL (row):   [4C93, UZ, google, 2026-04-29]
                    [4C93, RU, telegram, 2026-04-29]

ClickHouse (column): country: [UZ, RU, UZ, KZ...]

"UZ dan nechta click?" → faqat country ustunini o'qiydi → tez!
```

**Pipeline:**
```
Click → Redis (tez redirect)
      → ClickHouse (async, orqada)
      → Dashboard (real-time grafik)
```

---

## 17. OLTP va OLAP nima?

### OLTP — Online Transaction Processing
Kundalik operatsiyalar uchun — tez, kichik so'rovlar.
```
Misol: URL saqlash, redirect, click +1
  Kam qator: 1-10 ta
  Tez: 1-5ms
  Ko'p marta: sekundiga minglab
```

### OLAP — Online Analytical Processing
Tahlil uchun — katta, murakkab so'rovlar.
```
Misol: "30 kunlik grafik", "geo taqsimlash"
  Ko'p qator: millionlab
  Murakkab hisob
  Kam marta: kuniga bir necha marta
```

### Taqqoslash

| | OLTP | OLAP |
|--|--|--|
| Maqsad | Operatsiya | Tahlil |
| So'rov | 1-10 qator | Millionlab |
| Tezlik | 1-5ms | 0.1-10s |
| Bizda | PostgreSQL | ClickHouse |

---

## 18. Async Pipeline nima?

Vazifalarni ketma-ket emas, parallel bajarish.

**Sync (ketma-ket):**
```
GET /4C93:
  1. Redis → URL oldi    (0.8ms)
  2. ClickHouse yozdi    (5ms) ← foydalanuvchi kutdi!
  3. Redirect

Foydalanuvchi: 5.8ms kutdi ❌
```

**Async (parallel):**
```
GET /4C93:
  1. Redis → URL oldi    (0.8ms)
  2. Redirect ✅          ← foydalanuvchi ketdi!
     └→ Background: ClickHouse yozdi (5ms) ← kutmadi!

Foydalanuvchi: 0.8ms ✅
```

---

## 19. Aggregation Queries nima?

Ko'p qatorlarni yig'ib, bitta natija chiqaradigan so'rovlar.

**Asosiy funksiyalar:**
```sql
COUNT(*)  → nechta qator
SUM()     → yig'indisi
AVG()     → o'rtachasi
GROUP BY  → guruhlab hisoblash
```

**Bizning loyihada:**
```sql
-- Kunlik grafik
SELECT toDate(event_time) as kun, COUNT(*) as clicklar
FROM click_events
WHERE short_code = '4C93'
GROUP BY kun

-- Geo taqsimlash
SELECT country_code, COUNT(*) as clicklar
FROM click_events
GROUP BY country_code
ORDER BY clicklar DESC
```

---

## 20. Open-Source Analoglar

### YOURLS
```
2009 yil, PHP + MySQL
Eski arxitektura, plugin tizimi
Redis yo'q, ClickHouse yo'q
Qachon yaxshi: tez o'rnatish, PHP jamoa
```

### Shlink
```
2016 yil, PHP + Symfony
Docker ready, to'liq REST API
Redis zaif, ClickHouse yo'q
Qachon yaxshi: PHP jamoa, API muhim
```

### Kutt
```
2019 yil, Node.js + PostgreSQL + Redis
Eng yaqin analog bizga
ClickHouse yo'q, Async pipeline yo'q
Qachon yaxshi: Node.js jamoa
```

### url-shortener (PyPI)
```
Python kutubxona
Tashqi servis ishlatadi (TinyURL, bit.ly)
O'z serverda ishlamaydi
Faqat reference sifatida ko'rib chiqdik
```

### Taqqoslash

| | YOURLS | Shlink | Kutt | POC-014 |
|--|--|--|--|--|
| Til | PHP | PHP | Node.js | Python ✅ |
| Redis | ❌ | △ | ✅ | ✅ |
| ClickHouse | ❌ | ❌ | ❌ | ✅ |
| Async | ❌ | ❌ | △ | ✅ |
| WebSocket | ❌ | ❌ | ❌ | ✅ |

---

## 21. bit.ly nima?

Dunyodagi eng mashhur URL shortener servis.

```
2008 yilda yaratilgan, New York, AQSh
Kuniga 10 milliarddan ortiq redirect
500 million+ foydalanuvchi
```

**Texnik stack:**
```
Backend:   Java, Scala
Cache:     Redis (bizga o'xshash!)
DB:        Cassandra, MySQL
Analytics: Kafka + Hadoop
```

**Nima uchun Uzinfocom uchun mos emas:**
```
Ma'lumotlar AQSh serverida → maxfiylik ❌
Pullik → har oy xarajat
O'zbek tili → yo'q
Davlat portal → tashqi servisga bog'liqlik ❌
```

---

## 22. Amaliyotlar

 - [Sprint 1. FastAPI, PostgreSQL, React, URL Shortener. Base62](sprint-1.md)  
 - [Sprint 2. ClickHouse. Click event logger. Analytics. Rate limiting. QR Code](sprint-2.md)  
 - [Sprint 3. Analytics Dashboard](sprint-3.md)  
 - [Sprint 4. Part 1. Load Testing](tests/README.md)  
 - [Sprint 4. Part 2. Prometheus va Error Handling](sprint-4.md)  

*POC-014 · Uzinfocom R&D · Aprel 2026*