import { useEffect, useState } from 'react'

export default function LinksList({ onSelect }) {
  const [links, setLinks] = useState([])

  useEffect(() => {
    fetch('/api/v1/links')
      .then(r => r.json())
      .then(setLinks)
  }, [])

  if (!links.length) return null

  return (
    <div className="mt-6 bg-white rounded-2xl shadow p-6">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">
        Havolalar ro'yxati
      </h2>
      <div className="space-y-3">
        {links.map(link => (
          <div
            key={link.short_code}
            onClick={() => onSelect(link)}
            className="border border-gray-100 rounded-xl p-3 cursor-pointer hover:border-blue-300 hover:bg-blue-50 transition-colors"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-blue-600">
                {link.short_url}
              </span>
              <div className="flex items-center gap-2">
                {link.is_custom && (
                  <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full">
                    custom
                  </span>
                )}
                {link.expires_at && (
                  <span className="text-xs bg-amber-100 text-amber-600 px-2 py-0.5 rounded-full">
                    {new Date(link.expires_at).toLocaleDateString('uz-UZ')}
                  </span>
                )}
              </div>
            </div>
            <p className="text-xs text-gray-400 truncate">{link.long_url}</p>
            <div className="flex gap-3 mt-1.5">
              <span className="text-xs text-gray-400">
                {link.click_count} click
              </span>
              <span className="text-xs text-gray-400">
                {new Date(link.created_at).toLocaleDateString('uz-UZ')}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
