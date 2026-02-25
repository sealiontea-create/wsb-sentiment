import { useState, useEffect, useCallback } from 'react'
import TimeframeSelector from './components/TimeframeSelector'
import TickerTape from './components/TickerTape'
import TickerTable from './components/TickerTable'
import EarningsOracle from './components/EarningsOracle'
import OptionsFlow from './components/OptionsFlow'

const REFRESH_INTERVAL = 5 * 60 * 1000

const WSB_WISDOM = [
  "positions or ban",
  "buy high, sell low — this is the way",
  "it literally can't go tits up",
  "sir, this is a Wendy's",
  "stonks only go up",
  "GUH",
  "my wife's boyfriend said this is a good app",
  "this is not financial advice. we eat crayons here",
  "apes together strong",
  "diamond hands or no hands",
  "ban if no screenshots",
  "bears r fuk",
  "the market can stay irrational longer than you can stay solvent",
  "priced in",
  "the real DD was the friends we made along the way",
  "if Cramer says buy, you sell",
  "I'm not a financial advisor, I can barely read",
  "HODL until you can't feel feelings anymore",
  "loss porn is the real content",
  "somebody call an adult",
  "I put my life savings into this and I can't even read a balance sheet",
  "this is a casino and the house always wins",
  "imagine doing research before buying options",
  "the stock market is just astrology for men",
  "I asked my cat and she said buy calls",
  "Wendy's dumpster shifts are back on the menu",
  "positions: 100% portfolio in one ticker, expiring Friday",
  "the only hedge I know is the one in my front yard",
  "not a bear market if you don't look at your portfolio",
  "I'm financially ruined but at least I have Reddit karma",
]

export default function App() {
  const [hours, setHours] = useState(24)
  const [tickers, setTickers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scraping, setScraping] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [selectedTicker, setSelectedTicker] = useState(null)
  const [wisdomIdx, setWisdomIdx] = useState(() => Math.floor(Math.random() * WSB_WISDOM.length))

  useEffect(() => {
    const timer = setInterval(() => {
      setWisdomIdx(prev => (prev + 1) % WSB_WISDOM.length)
    }, 8000)
    return () => clearInterval(timer)
  }, [])

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
      <TickerTape tickers={tickers} />

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
        <div className="wisdom" key={wisdomIdx}>{WSB_WISDOM[wisdomIdx]}</div>
        <div className="footer-sub">
          auto-refreshes every 5 min &bull; data from r/wallstreetbets &bull; not financial advice
        </div>
      </div>
    </>
  )
}
