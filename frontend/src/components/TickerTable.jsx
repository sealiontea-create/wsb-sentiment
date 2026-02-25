import { useState } from 'react'

function formatUpvotes(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k'
  return String(n)
}

function sentimentClass(score) {
  if (score >= 0.1) return 'bullish'
  if (score <= -0.1) return 'bearish'
  return 'neutral'
}

function sentimentText(score) {
  if (score >= 0.1) return `+${score.toFixed(2)}`
  return score.toFixed(2)
}

function vibeEmoji(score, mentions) {
  if (mentions >= 10 && score >= 0.3) return '🚀'
  if (mentions >= 10 && score <= -0.3) return '💀'
  if (score >= 0.5) return '🔥'
  if (score >= 0.1) return '📈'
  if (score <= -0.5) return '🩸'
  if (score <= -0.1) return '📉'
  return '😐'
}

const COLUMNS = [
  { key: 'rank', label: '#', sortable: false, tip: 'Rank — higher = more regarded' },
  { key: 'ticker', label: 'Ticker', sortable: true, tip: 'The stock your wife\'s boyfriend is probably already in' },
  { key: 'mention_count', label: 'Mentions', sortable: true, tip: 'How many apes are screaming about this in posts + comments' },
  { key: 'avg_sentiment', label: 'Sentiment', sortable: true, tip: 'Vibes only — ranges from -1 (GUH) to +1 (moon)' },
  { key: 'unique_authors', label: 'Apes', sortable: true, tip: 'Unique degenerates talking about this ticker' },
  { key: 'top_upvotes', label: 'Top Post', sortable: true, tip: 'Upvotes on the most viral post — high number = someone\'s loss porn went big' },
]

export default function TickerTable({ tickers, selectedTicker, onTickerClick }) {
  const [sortKey, setSortKey] = useState('mention_count')
  const [sortDesc, setSortDesc] = useState(true)

  const sorted = [...tickers].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    if (typeof av === 'string') return sortDesc ? bv.localeCompare(av) : av.localeCompare(bv)
    return sortDesc ? bv - av : av - bv
  })

  function handleSort(key) {
    if (!COLUMNS.find(c => c.key === key)?.sortable) return
    if (sortKey === key) {
      setSortDesc(!sortDesc)
    } else {
      setSortKey(key)
      setSortDesc(true)
    }
  }

  return (
    <table className="ticker-table">
      <thead>
        <tr>
          {COLUMNS.map((col) => (
            <th
              key={col.key}
              className={sortKey === col.key ? 'sorted' : ''}
              onClick={() => handleSort(col.key)}
              title={col.tip}
            >
              {col.label}
              {sortKey === col.key && col.sortable && (
                <span className="sort-arrow">{sortDesc ? '▼' : '▲'}</span>
              )}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sorted.map((t, i) => {
          const cls = sentimentClass(t.avg_sentiment)
          const barWidth = Math.min(Math.abs(t.avg_sentiment) * 50, 50)
          return (
            <tr
              key={t.ticker}
              className={selectedTicker === t.ticker ? 'ticker-selected' : ''}
              onClick={() => onTickerClick?.(t.ticker)}
              style={{ cursor: 'pointer' }}
            >
              <td className="rank-cell">{i + 1}</td>
              <td>
                <div className="ticker-cell">
                  <span className="ticker-symbol">${t.ticker}</span>
                  <span className="ticker-vibe">
                    {vibeEmoji(t.avg_sentiment, t.mention_count)}
                  </span>
                </div>
              </td>
              <td className="mention-count">{t.mention_count}</td>
              <td>
                <div className="sentiment-cell">
                  <div className="sentiment-bar-bg">
                    <div
                      className={`sentiment-bar-fill ${cls}`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <span className={`sentiment-score ${cls}`}>
                    {sentimentText(t.avg_sentiment)}
                  </span>
                </div>
              </td>
              <td className="upvotes">{t.unique_authors}</td>
              <td className="upvotes">{formatUpvotes(t.top_upvotes)}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
