import { useState, useEffect } from 'react'

export default function OptionsFlow({ hours }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/options?hours=${hours}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [hours])

  if (loading) return null
  if (!data || !data.summary || data.summary.total_options === 0) return null

  const { summary, flow } = data
  const ratio = summary.call_put_ratio
  const callPct = Math.round((summary.calls / Math.max(summary.total_options, 1)) * 100)
  const putPct = 100 - callPct

  return (
    <div className="options-section">
      <div className="options-header">
        <h2>Options Flow</h2>
        <span className="options-subtitle">positions scraped from comments</span>
      </div>

      <div className="options-stats">
        <div className="options-ratio-bar">
          <div className="ratio-calls" style={{ width: `${callPct}%` }}>
            {callPct > 15 && `${summary.calls} calls`}
          </div>
          <div className="ratio-puts" style={{ width: `${putPct}%` }}>
            {putPct > 15 && `${summary.puts} puts`}
          </div>
        </div>
        <div className="options-ratio-label">
          C/P ratio: <span className={ratio >= 1 ? 'green' : 'red'}>{ratio}</span>
          {' '}&mdash;{' '}
          {ratio >= 2 ? 'apes are yoloing calls' :
           ratio >= 1.2 ? 'leaning bullish' :
           ratio >= 0.8 ? 'roughly balanced' :
           ratio >= 0.5 ? 'leaning bearish' :
           'put city'}
        </div>
      </div>

      {flow.length > 0 && (
        <table className="options-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Type</th>
              <th>Count</th>
              <th>Strike Range</th>
              <th>Expiry</th>
            </tr>
          </thead>
          <tbody>
            {flow.map((f, i) => (
              <tr key={i}>
                <td className="ticker-symbol">${f.ticker}</td>
                <td>
                  <span className={`opt-badge ${f.option_type}`}>
                    {f.option_type === 'call' ? 'CALL' : 'PUT'}
                  </span>
                </td>
                <td className="mention-count">{f.count}</td>
                <td className="strike-range">
                  {f.min_strike === f.max_strike
                    ? `$${f.min_strike}`
                    : `$${f.min_strike} — $${f.max_strike}`
                  }
                </td>
                <td className="expiry-cat">
                  {formatExpiry(f.expiry_categories)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {(summary.top_calls.length > 0 || summary.top_puts.length > 0) && (
        <div className="top-plays">
          {summary.top_calls.length > 0 && (
            <div className="top-plays-col">
              <h3>Top Bull Plays</h3>
              {summary.top_calls.map((p, i) => (
                <div key={i} className="play-card bull">
                  <span className="play-raw">{p.raw_match}</span>
                  {p.expiry_category && (
                    <span className="play-expiry">{p.expiry_category}</span>
                  )}
                </div>
              ))}
            </div>
          )}
          {summary.top_puts.length > 0 && (
            <div className="top-plays-col">
              <h3>Top Bear Plays</h3>
              {summary.top_puts.map((p, i) => (
                <div key={i} className="play-card bear">
                  <span className="play-raw">{p.raw_match}</span>
                  {p.expiry_category && (
                    <span className="play-expiry">{p.expiry_category}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function formatExpiry(cats) {
  if (!cats) return '—'
  const unique = [...new Set(cats.split(',').filter(Boolean))]
  return unique.join(', ') || '—'
}
