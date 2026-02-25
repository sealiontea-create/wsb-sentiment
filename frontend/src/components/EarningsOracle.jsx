import { useState, useEffect } from 'react'

function classColor(cls) {
  if (cls === 'MOON' || cls === 'PUMP') return 'green'
  if (cls === 'TANK' || cls === 'DIP') return 'red'
  return 'dim'
}

function classEmoji(cls) {
  if (cls === 'MOON') return '🚀'
  if (cls === 'PUMP') return '📈'
  if (cls === 'FLAT') return '😐'
  if (cls === 'DIP') return '📉'
  if (cls === 'TANK') return '💀'
  return ''
}

function formatMove(pct) {
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(1)}%`
}

export default function EarningsOracle({ symbol, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setData(null)

    fetch(`/api/earnings/${symbol}`)
      .then(res => {
        if (!res.ok) throw new Error(`API returned ${res.status}`)
        return res.json()
      })
      .then(d => {
        if (d.error) {
          setError(d.error)
        } else {
          setData(d)
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [symbol])

  return (
    <div className="earnings-oracle">
      <div className="eo-header">
        <div className="eo-title">
          <span className="eo-icon">🔮</span>
          <h2>Earnings Oracle — <span className="gold">${symbol}</span></h2>
        </div>
        <button className="eo-close" onClick={onClose} title="Close">✕</button>
      </div>

      {loading ? (
        <div className="eo-loading">
          <div className="spinner" />
          <p>Consulting the crystal ball...</p>
        </div>
      ) : error ? (
        <div className="eo-error">
          <div className="eo-error-icon">🔮💔</div>
          <p>Crystal ball is broken</p>
          <p className="eo-error-detail">{error}</p>
        </div>
      ) : data ? (
        <>
          <div className="eo-stats">
            <div className="eo-stat moon">
              <div className="eo-stat-value">{data.moon_pct}%</div>
              <div className="eo-stat-label">Moon</div>
            </div>
            <div className="eo-stat tank">
              <div className="eo-stat-value">{data.tank_pct}%</div>
              <div className="eo-stat-label">Tank</div>
            </div>
            <div className="eo-stat neutral">
              <div className="eo-stat-value">{formatMove(data.avg_move)}</div>
              <div className="eo-stat-label">Avg Move</div>
            </div>
            <div className="eo-stat guh">
              <div className="eo-stat-value">{data.guh_score}</div>
              <div className="eo-stat-label">GUH Score</div>
            </div>
          </div>

          <div className="eo-commentary">{data.commentary}</div>

          <div className="eo-meta">
            {data.events} earnings over {data.years_covered} years
            {data.streak >= 2 && (
              <> — <span className={data.streak_direction === 'moon' ? 'green' : data.streak_direction === 'tank' ? 'red' : ''}>
                {data.streak} {data.streak_direction}s in a row
              </span></>
            )}
            {data.cached && <span className="eo-cached"> (cached)</span>}
          </div>

          <div className="eo-extremes">
            <span className="green">Best: {formatMove(data.max_moon)}</span>
            <span className="eo-sep">|</span>
            <span className="red">Worst: {formatMove(data.max_tank)}</span>
            <span className="eo-sep">|</span>
            <span>Volatility: {data.volatility.toFixed(1)}</span>
          </div>

          <div className="eo-history">
            <div className="eo-history-title">Earnings History</div>
            {data.history.map((h, i) => {
              const barPct = Math.min(Math.abs(h.move_pct) * 3, 100)
              const isPositive = h.move_pct >= 0
              return (
                <div key={i} className="eo-bar-row">
                  <div className="eo-bar-date">{h.date}</div>
                  <div className="eo-bar-container">
                    <div className="eo-bar-track">
                      {isPositive ? (
                        <div
                          className="eo-bar-fill green-bg"
                          style={{ width: `${barPct}%`, marginLeft: '50%' }}
                        />
                      ) : (
                        <div
                          className="eo-bar-fill red-bg"
                          style={{ width: `${barPct}%`, marginLeft: `${50 - barPct}%` }}
                        />
                      )}
                      <div className="eo-bar-center" />
                    </div>
                  </div>
                  <div className={`eo-bar-value ${isPositive ? 'green' : 'red'}`}>
                    {formatMove(h.move_pct)}
                  </div>
                  <div className="eo-bar-class">
                    {classEmoji(h.classification)}
                  </div>
                  <div className="eo-bar-eps">
                    {h.surprise_pct !== null ? (
                      <span className={h.surprise_pct >= 0 ? 'green' : 'red'}>
                        EPS {h.surprise_pct >= 0 ? '+' : ''}{h.surprise_pct}%
                      </span>
                    ) : (
                      <span className="dim">—</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="eo-disclaimer">
            entertainment only — past earnings moves don't predict future results — this is a casino
          </div>
        </>
      ) : null}
    </div>
  )
}
