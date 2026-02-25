import { useState, useEffect, useCallback } from 'react'
import TimeframeSelector from './components/TimeframeSelector'
import TickerTable from './components/TickerTable'
import EarningsOracle from './components/EarningsOracle'
import OptionsFlow from './components/OptionsFlow'

const REFRESH_INTERVAL = 5 * 60 * 1000

export default function App() {
  const [hours, setHours] = useState(24)
  const [tickers, setTickers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scraping, setScraping] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [selectedTicker, setSelectedTicker] = useState(null)

  const fetchTickers = useCallback(async () => {
    try {
      setError(null)
      const res = await fetch(`/api/tickers?hours=${hours}&limit=50`)
      if (!res.ok) throw new Error(`API returned ${res.status}`)
      const data = await res.json()
      setTickers(data.tickers)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [hours])

  useEffect(() => {
    setLoading(true)
    fetchTickers()
    const interval = setInterval(fetchTickers, REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchTickers])

  async function handleScrape() {
    setScraping(true)
    try {
      const res = await fetch('/api/scrape', { method: 'POST' })
      if (!res.ok) throw new Error(`Scrape failed: ${res.status}`)
      await fetchTickers()
    } catch (err) {
      setError(err.message)
    } finally {
      setScraping(false)
    }
  }

  // Stats from current data
  const bullCount = tickers.filter(t => t.avg_sentiment >= 0.1).length
  const bearCount = tickers.filter(t => t.avg_sentiment <= -0.1).length
  const totalMentions = tickers.reduce((sum, t) => sum + t.mention_count, 0)

  return (
    <>
      <div className="header">
        <span className="header-icon">🦍</span>
        <h1>WSB <span className="gold">Sentiment</span> Tracker</h1>
        <p className="tagline">
          what r/wallstreetbets is losing money on right now
          <br />
          <span>not financial advice &mdash; we eat crayons here</span>
        </p>
      </div>

      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-value gold">{totalMentions}</div>
          <div className="stat-label">Mentions</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{tickers.length}</div>
          <div className="stat-label">Tickers</div>
        </div>
        <div className="stat-card">
          <div className="stat-value green">{bullCount}</div>
          <div className="stat-label">Bullish</div>
        </div>
        <div className="stat-card">
          <div className="stat-value red">{bearCount}</div>
          <div className="stat-label">Bearish</div>
        </div>
      </div>

      <div className="controls-bar">
        <TimeframeSelector hours={hours} onChange={setHours} />
        <div className="controls-right">
          {lastUpdated && (
            <span className="last-updated">
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            className="scrape-btn"
            onClick={handleScrape}
            disabled={scraping}
          >
            {scraping ? '🔄 Scraping...' : '🚀 Scrape WSB'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
          <p>Consulting the apes...</p>
        </div>
      ) : error ? (
        <div className="error-state">
          <div className="error-icon">💀</div>
          <p>{error}</p>
          <p className="error-hint">
            Backend probably died. Start it with: uvicorn api:app --port 8000
          </p>
        </div>
      ) : tickers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🦧</div>
          <p>No data yet. The apes haven't spoken.</p>
          <p className="empty-hint">
            Hit "Scrape WSB" to pull fresh degeneracy from the sub.
          </p>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <TickerTable
              tickers={tickers}
              selectedTicker={selectedTicker}
              onTickerClick={(t) => setSelectedTicker(prev => prev === t ? null : t)}
            />
          </div>
          {selectedTicker && (
            <EarningsOracle
              symbol={selectedTicker}
              onClose={() => setSelectedTicker(null)}
            />
          )}
        </>
      )}

      <OptionsFlow hours={hours} />

      <div className="footer">
        positions or ban &bull; this is a casino &bull; sir this is a wendy's
        <br />
        auto-refreshes every 5 min &bull; your wife's boyfriend approves this app
      </div>
    </>
  )
}
