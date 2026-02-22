const TIMEFRAMES = [
  { label: '24h', hours: 24 },
  { label: '48h', hours: 48 },
  { label: '72h', hours: 72 },
]

export default function TimeframeSelector({ hours, onChange }) {
  return (
    <div className="timeframe-bar">
      {TIMEFRAMES.map((tf) => (
        <button
          key={tf.hours}
          className={`timeframe-btn ${hours === tf.hours ? 'active' : ''}`}
          onClick={() => onChange(tf.hours)}
        >
          {tf.label}
        </button>
      ))}
    </div>
  )
}
