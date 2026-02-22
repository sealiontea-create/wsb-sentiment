# WSB Sentiment Tracker

Free web app that scrapes r/wallstreetbets, identifies most-mentioned tickers, scores bullish/bearish sentiment over selectable timeframes (24h/48h/72h).

## Stack
- **Backend:** Python 3 + FastAPI + VADER Sentiment + SQLite
- **Frontend:** Vite + React (dark theme, Inter + JetBrains Mono fonts)
- **Reddit data:** Direct public JSON endpoints (`reddit.com/r/wallstreetbets/*.json`) — no API key needed
- **Cost:** $0

## File Inventory

### Backend (`backend/`)
| File | Purpose |
|------|---------|
| `api.py` | FastAPI app — `/api/tickers`, `/api/ticker/{symbol}`, `/api/status`, `/api/scrape` |
| `run_scraper.py` | Pipeline orchestrator: scrape → extract → score → store. `run_pipeline()` entry point. |
| `scraper.py` | HTTP-based Reddit scraper (no PRAW/API key). Fetches hot + new + rising posts, comments with recursive reply extraction. Prioritizes daily/weekly megathreads. |
| `tickers.py` | Ticker extraction via `$TICKER` + uppercase patterns, 150+ word blocklist, SEC EDGAR validation (cached) |
| `sentiment.py` | VADER + ~50 WSB custom terms + 16 emoji sentiment scores (rockets, skulls, etc.) |
| `db.py` | SQLite schema, query helpers, batch insert. Aggregation returns unique_authors + top_upvotes per ticker. |
| `data/` | SQLite DB (`wsb.db`) + SEC ticker cache (`sec_tickers.json`) — gitignored |
| `requirements.txt` | vaderSentiment, fastapi, uvicorn (no PRAW, no python-dotenv) |

### Frontend (`frontend/`)
| File | Purpose |
|------|---------|
| `src/App.jsx` | Dashboard — stats cards, timeframe state, auto-refresh 5min, scrape trigger, WSB humor |
| `src/components/TickerTable.jsx` | Sortable table: ticker + vibe emoji, mentions, sentiment bar, apes (unique authors), top post upvotes |
| `src/components/TimeframeSelector.jsx` | 24h/48h/72h toggle buttons |
| `src/index.css` | Dark theme (#0a0a0a bg), Inter + JetBrains Mono fonts, green/red/gold accents, sentiment bars, responsive |
| `vite.config.js` | Dev proxy /api → localhost:8000 |
| `index.html` | Entry point |

## Running Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn api:app --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # → localhost:3000
```

### First scrape
Either hit "Scrape WSB" in the UI, or:
```bash
cd backend
python run_scraper.py
```

A full scrape takes ~2 minutes (200 hot + 200 new + 50 rising posts, comments from top 50 posts including all megathreads).

## API Endpoints
- `GET /api/tickers?hours=24&limit=25` — Top tickers with mention_count, avg_sentiment, unique_authors, top_upvotes
- `GET /api/ticker/{symbol}?hours=24` — Individual mentions for a ticker
- `GET /api/status` — DB stats (total mentions, unique tickers, latest timestamp)
- `POST /api/scrape` — Trigger scrape pipeline, returns stats

## Key Decisions
- **No Reddit API key needed** — uses public JSON endpoints (`/r/wallstreetbets/hot.json`, etc.) with 1.2s delay between requests
- **Dropped PRAW** — Reddit locked API app registration behind manual approval process. Public JSON endpoints work fine for read-only scraping.
- VADER + custom WSB lexicon (free, good enough) over paid NLP APIs
- Aggressive blocklist (150+ words) over NLP disambiguation (simple, debuggable)
- SQLite over Postgres (zero setup, single file)
- `$TICKER` = high confidence (skip blocklist); bare uppercase = filtered against blocklist + SEC list
- Emoji sentiment (rockets, moon, skull, etc.) blended 30% into VADER scores
- **Megathread priority** — daily/weekly discussion threads get scraped first with 3x comment limits since that's where ticker talk lives
- **Recursive comment extraction** — follows reply chains up to 3 levels deep
- **"Apes" column** = unique authors mentioning a ticker (more honest than summing upvotes across unrelated posts)
- **"Top Post" column** = highest-upvoted single post/comment mentioning that ticker
- Vibe emojis on tickers: 🚀 hot bull, 💀 heavy bear, 🔥 strong bull, 📈 bull, 🩸 strong bear, 📉 bear, 😐 neutral

## Scraper Details
- Fetches: 200 hot + 200 new + 50 rising posts (~200 unique after dedup)
- Comments: top 50 posts by upvotes, prioritizing megathreads (daily discussion, earnings, weekend thread)
- Megathreads get 150 comments each, regular posts get 50
- Recursive reply extraction (3 levels deep)
- 1.2s delay between requests to respect rate limits
- ~905 mentions per scrape, ~2 min runtime
- SEC EDGAR ticker list cached locally (10,382 valid tickers)

## TODO
- [ ] Deploy (Render/Railway backend, Cloudflare Pages frontend)
- [ ] Add ads if it gets traffic
- [ ] Historical charts per ticker
- [ ] Meme/copypasta detection for noise filtering (downweight "Meme" flair posts)
- [ ] Scheduled scraping (cron every 30min)
