# POC-014 — Leaflet Choropleth Geo Xarita

**Muallif:** Rovshen R. Ashirov  
**Loyiha:** POC-014 URL Shortener  
**Sana:** May 2026  
**Holat:** ✅ Tugallandi

---

## Maqsad

Confluence da berilgan:
```
Click analytics dashboard:
  График кликов по времени,
  карта гео-распределения,   ← shu
  top referrers.
  Данные обновляются в реальном времени.

Browser API / технология: Chart.js, Leaflet choropleth, WebSocket
```

Geo taqsimlashni jadval ko'rinishida yozgan edik — bu yetarli emas edi. Leaflet bilan interaktiv xarita qo'shildi.

---

## Leaflet va Choropleth nima?

### Leaflet
```
Brauzerda interaktiv xarita ko'rsatuvchi
JavaScript kutubxona.

Imkoniyatlari:
  → OpenStreetMap dan xarita yuklaydi
  → Zoom (kattalashtirish) ishlaydi
  → Pan (xaritani siljitish) ishlaydi
  → Marker, popup, circle qo'shish mumkin
```

### Choropleth
```
Ma'lumotga qarab hududlarni
rang yoki hajm bilan ko'rsatish usuli.

Oddiy misol:
  Saylov xaritasi:
    Toshkent → ko'p ovoz → to'q rang
    Navoiy   → kam ovoz → och rang

Bizda:
  UZ → 100% click → katta doira
  RU → 28% click  → o'rta doira
  KZ → 12% click  → kichik doira

Doira hajmi = click soni
```

---

## O'rnatish

```bash
cd ~/POC/poc014-app/frontend
npm install leaflet
```

---

## `GeoMap.jsx` komponenti

**Fayl:** `frontend/src/GeoMap.jsx`

```jsx
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Davlat kodi → koordinatalar
const COUNTRY_COORDS = {
  UZ: [41.2995, 69.2401],
  RU: [55.7558, 37.6173],
  KZ: [51.1801, 71.4460],
  DE: [52.5200, 13.4050],
  US: [38.9072, -77.0369],
  GB: [51.5074, -0.1278],
  CN: [39.9042, 116.4074],
  TR: [39.9334, 32.8597],
  FR: [48.8566, 2.3522],
  JP: [35.6762, 139.6503],
}

export default function GeoMap({ geo }) {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)

  useEffect(() => {
    if (!geo || !geo.length || !mapRef.current) return

    // Avvalgi xaritani o'chiramiz
    if (mapInstance.current) {
      mapInstance.current.remove()
      mapInstance.current = null
    }

    // Xarita yaratamiz
    const map = L.map(mapRef.current, {
      center: [40, 60],
      zoom: 2,
      zoomControl: true,
      scrollWheelZoom: false,
    })

    mapInstance.current = map

    // OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap'
    }).addTo(map)

    // Har bir davlat uchun circle marker
    const maxClicks = Math.max(...geo.map(g => g.clicks))

    geo.forEach(g => {
      const coords = COUNTRY_COORDS[g.country_code]
      if (!coords) return

      // Radius click soniga qarab (8-23 px)
      const radius = 8 + (g.clicks / maxClicks) * 15

      L.circleMarker(coords, {
        radius,
        fillColor: '#2563eb',
        color: '#1d4ed8',
        weight: 2,
        opacity: 0.8,
        fillOpacity: 0.5,
      })
        .bindPopup(`
          <b>${g.country_code}</b><br/>
          ${g.clicks} clicks<br/>
          ${g.pct}%
        `)
        .addTo(map)
    })

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove()
        mapInstance.current = null
      }
    }
  }, [geo])

  if (!geo || !geo.length) return null

  return (
    <div>
      <p className="text-xs font-medium text-gray-500 mb-2">
        Geografik taqsimlash (xarita)
      </p>
      <div
        ref={mapRef}
        style={{ height: '200px', borderRadius: '8px', zIndex: 0 }}
      />
    </div>
  )
}
```

### Tushuntirish

**`useRef` — 2 ta maqsad:**
```
mapRef       → DOM elementiga murojaat (div)
mapInstance  → Leaflet xarita obyektini saqlash

Nima uchun ref?
  useState ishlatsa → har render da yangi xarita yaratiladi
  useRef → bir marta yaratiladi, saqlanadi
```

**`useEffect` cleanup:**
```javascript
return () => {
  if (mapInstance.current) {
    mapInstance.current.remove()  // xaritani tozalaydi
    mapInstance.current = null
  }
}
```
```
Komponent o'chganda yoki geo o'zgarganda:
  Eski xarita o'chiriladi
  Yangi xarita yaratiladi
  Xotira sızıntısı bo'lmaydi
```

**Radius formula:**
```
radius = 8 + (g.clicks / maxClicks) * 15

maxClicks = eng ko'p click olgan davlat

UZ: 100 click, max=100 → 8 + (100/100)*15 = 23px (katta)
RU: 28 click,  max=100 → 8 + (28/100)*15  = 12px (o'rta)
KZ: 12 click,  max=100 → 8 + (12/100)*15  = 10px (kichik)
```

**`scrollWheelZoom: false`:**
```
Foydalanuvchi sahifani scroll qilganda
xarita zoom bo'lmasin deb o'chirildi
```

---

## `Dashboard.jsx` ga ulash

**Import:**
```jsx
import GeoMap from './GeoMap'
```

**Geo bar chart dan oldin:**
```jsx
<GeoMap geo={geo} />
```

---

## Natija

```
Xarita: OpenStreetMap (bepul, ochiq)
UZ    → katta ko'k doira (100%)
Zoom  → + / - tugmalar ishlaydi
Popup → doiraga bosganда:
         UZ
         1 clicks
         100%
```

---

## COUNTRY_COORDS haqida

```
Hozir 10 ta davlat koordinatasi hardcoded:
  UZ, RU, KZ, DE, US, GB, CN, TR, FR, JP

Yangi davlat qo'shish:
  COUNTRY_COORDS ga qo'shish yetarli:
  XX: [latitude, longitude]

Kelajakda:
  GeoIP2 + MaxMind → haqiqiy davlat kodi
  Koordinatalar → REST Countries API dan olish mumkin
```

---

## Definition of Done

| Mezon | Natija |
|-------|--------|
| Leaflet xarita ko'rinmoqda | ✅ |
| Click soni bo'yicha doira hajmi | ✅ |
| Popup — davlat, click, foiz | ✅ |
| Zoom ishlaydi | ✅ |
| Confluence talabi bajarildi | ✅ |

---

*POC-014 · Uzinfocom R&D · May 2026*