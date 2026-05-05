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

      const radius = 8 + (g.clicks / maxClicks)

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
