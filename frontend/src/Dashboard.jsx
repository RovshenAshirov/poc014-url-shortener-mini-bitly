import { useEffect, useRef, useState } from 'react'
import Chart from 'chart.js/auto'

export default function Dashboard({ shortCode, shortUrl }) {
  const [stats, setStats] = useState(null)
  const [timeseries, setTimeseries] = useState([])
  const [geo, setGeo] = useState([])
  const [referrers, setReferrers] = useState([])
  const chartRef = useRef(null)
  const chartInstance = useRef(null)

  // WebSocket — real-time stats
  useEffect(() => {
    if (!shortCode) return
    const ws = new WebSocket(`ws://localhost:8000/ws/stats/${shortCode}`)
    ws.onmessage = (e) => setStats(JSON.parse(e.data))
    return () => ws.close()
  }, [shortCode])

  // Analytics ma'lumotlarini olish
  useEffect(() => {
    if (!shortCode) return

    fetch(`/api/v1/analytics/${shortCode}/timeseries`)
      .then(r => r.json()).then(setTimeseries)

    fetch(`/api/v1/analytics/${shortCode}/geo`)
      .then(r => r.json()).then(setGeo)

    fetch(`/api/v1/analytics/${shortCode}/referrers`)
      .then(r => r.json()).then(setReferrers)
  }, [shortCode])

  // Chart.js grafik
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
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } }
        }
      }
    })
  }, [timeseries])

  if (!shortCode) return null

  return (
    <div className="mt-6 bg-white rounded-2xl shadow p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700">Analytics</h2>
        <span className="flex items-center gap-1.5 text-xs text-green-600">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          Live
        </span>
      </div>

      {/* Metric cards */}
      {stats && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-xs text-gray-500 mb-1">Jami clicklar</p>
            <p className="text-2xl font-semibold text-gray-800">
              {stats.total_clicks.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-xs text-gray-500 mb-1">Bugun</p>
            <p className="text-2xl font-semibold text-gray-800">
              {stats.today_clicks.toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Timeseries grafik */}
      {timeseries.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">
            Clicklar (so'nggi 7 kun)
          </p>
          <canvas ref={chartRef} height="120"></canvas>
        </div>
      )}

      {/* Geo jadval */}
      {geo.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">
            Geografiya
          </p>
          <div className="space-y-2">
            {geo.map(g => (
              <div key={g.country_code} className="flex items-center gap-2">
                <span className="text-xs text-gray-600 w-8">
                  {g.country_code}
                </span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${g.pct}%` }}
                  ></div>
                </div>
                <span className="text-xs text-gray-500 w-10 text-right">
                  {g.pct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Referrers */}
      {referrers.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">
            Top referrerlar
          </p>
          <div className="space-y-2">
            {referrers.map(r => (
              <div key={r.domain} className="flex items-center gap-2">
                <span className="text-xs text-gray-600 w-24 truncate">
                  {r.domain}
                </span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${r.pct}%` }}
                  ></div>
                </div>
                <span className="text-xs text-gray-500 w-10 text-right">
                  {r.pct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
