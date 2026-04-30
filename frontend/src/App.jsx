import QRCode from 'qrcode'
import { useState, useEffect, useRef } from 'react'

export default function App() {
  const [longUrl, setLongUrl] = useState('')
  const [alias, setAlias] = useState('')
  const [ttl, setTtl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const canvasRef = useRef(null)

  async function handleShorten() {
    if (!longUrl) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const body = { long_url: longUrl }
      if (alias) body.alias = alias
      if (ttl) body.ttl_days = parseInt(ttl)
      const res = await fetch('/api/v1/shorten', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Xatolik yuz berdi'); return }
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
    } catch (e) {
      setError('Server bilan ulanishda xatolik')
    } finally {
      setLoading(false)
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(result.short_url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-blue-700">poc014.uz</h1>
          <p className="text-gray-500 mt-1">POC-014 — URL Shortener</p>
        </div>
        <div className="bg-white rounded-2xl shadow p-6 space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-600 mb-1 block">Uzun URL</label>
            <input
              type="text"
              value={longUrl}
              onChange={e => setLongUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleShorten()}
              placeholder="https://uzinfocom.uz/..."
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-sm font-medium text-gray-600 mb-1 block">Custom alias (ixtiyoriy)</label>
              <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden">
                <span className="px-3 py-2.5 bg-gray-50 text-gray-400 text-sm border-r border-gray-200">localhost:8000/</span>
                <input
                  type="text"
                  value={alias}
                  onChange={e => setAlias(e.target.value)}
                  placeholder="gov-portal"
                  className="flex-1 px-3 py-2.5 text-sm focus:outline-none"
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600 mb-1 block">Muddati</label>
              <select
                value={ttl}
                onChange={e => setTtl(e.target.value)}
                className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Doimiy</option>
                <option value="1">1 kun</option>
                <option value="7">7 kun</option>
                <option value="30">30 kun</option>
              </select>
            </div>
          </div>
          <button
            onClick={handleShorten}
            disabled={loading || !longUrl}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium py-2.5 rounded-lg transition-colors"
          >
            {loading ? 'Qisqartirilmoqda...' : 'Qisqartirish'}
          </button>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}
          {result && (
            <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3">
              <p className="text-xs text-gray-500 mb-1">Qisqa URL:</p>
              <div className="flex items-center justify-between gap-2">
                <a
                  href={result.short_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 font-medium text-sm hover:underline truncate"
                >
                  {result.short_url}
                </a>
                <button
                  onClick={handleCopy}
                  className="shrink-0 text-xs bg-white border border-gray-200 hover:bg-gray-50 px-3 py-1.5 rounded-lg transition-colors"
                >
                  {copied ? 'Nusxalandi' : 'Nusxalash'}
                </button>
              </div>
              {result.expires_at && (
                <p className="text-xs text-gray-400 mt-1">
                  Muddati: {new Date(result.expires_at).toLocaleDateString('uz-UZ')}
                </p>
              )}
              {/* QR Code */}
              <div className="mt-3 pt-3 border-t border-green-200">
                <p className="text-xs text-gray-500 mb-2">QR Code:</p>
                <div className="flex items-center gap-4">
                  <canvas ref={canvasRef} className="rounded" />
                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => {
                        const link = document.createElement('a')
                        link.download = `qr-${result.short_code}.png`
                        link.href = canvasRef.current.toDataURL()
                        link.click()
                      }}
                      className="text-xs bg-white border border-gray-200 hover:bg-gray-50 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      PNG yuklab olish
                    </button>
                    <button
                      onClick={() => {
                        const svgData = `<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><image href='${canvasRef.current.toDataURL()}' width='160' height='160'/></svg>`
                        const blob = new Blob([svgData], { type: 'image/svg+xml' })
                        const link = document.createElement('a')
                        link.download = `qr-${result.short_code}.svg`
                        link.href = URL.createObjectURL(blob)
                        link.click()
                      }}
                      className="text-xs bg-white border border-gray-200 hover:bg-gray-50 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      SVG yuklab olish
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        <p className="text-center text-xs text-gray-400 mt-4">Uzinfocom R&D · POC-014</p>
      </div>
    </div>
  )
}
