function vibeEmoji(score) {
  if (score >= 0.3) return '🚀'
  if (score >= 0.1) return '📈'
  if (score <= -0.3) return '💀'
  if (score <= -0.1) return '📉'
  return '😐'
}

export default function TickerTape({ tickers }) {
  if (!tickers || tickers.length === 0) return null

  // Double the list for seamless infinite scroll
  const items = [...tickers, ...tickers]

  return (
    <div className="ticker-tape">
      <div className="ticker-tape-track">
        {items.map((t, i) => (
          <span key={`${t.ticker}-${i}`} className="tape-item">
            <span className="tape-symbol">${t.ticker}</span>
            <span className={`tape-sentiment ${t.avg_sentiment >= 0.1 ? 'green' : t.avg_sentiment <= -0.1 ? 'red' : ''}`}>
              {t.avg_sentiment >= 0 ? '+' : ''}{t.avg_sentiment.toFixed(2)}
            </span>
            <span className="tape-emoji">{vibeEmoji(t.avg_sentiment)}</span>
            <span className="tape-mentions">{t.mention_count}x</span>
          </span>
        ))}
      </div>
    </div>
  )
}
