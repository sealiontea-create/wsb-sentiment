import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
from db import init_db, get_top_tickers, get_ticker_detail, get_db_stats, get_options_flow, get_options_summary, get_earnings_cache, set_earnings_cache
from run_scraper import run_pipeline
from earnings import fetch_earnings_data

app = FastAPI(title="WSB Sentiment Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Serve built frontend in production
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


@app.get("/api/tickers")
def api_tickers(hours: int = Query(24, ge=1, le=168), limit: int = Query(25, ge=1, le=100)):
    """Get top mentioned tickers with aggregated sentiment."""
    tickers = get_top_tickers(hours=hours, limit=limit)
    return {"tickers": tickers, "hours": hours, "count": len(tickers)}


@app.get("/api/ticker/{symbol}")
def api_ticker_detail(symbol: str, hours: int = Query(24, ge=1, le=168)):
    """Get individual mentions for a specific ticker."""
    mentions = get_ticker_detail(symbol, hours=hours)
    return {"symbol": symbol.upper(), "mentions": mentions, "hours": hours, "count": len(mentions)}


@app.get("/api/status")
def api_status():
    """Get database stats and last scrape info."""
    stats = get_db_stats()
    return stats


@app.get("/api/options")
def api_options(hours: int = Query(24, ge=1, le=168)):
    """Get options flow summary + top plays."""
    summary = get_options_summary(hours=hours)
    flow = get_options_flow(hours=hours)
    return {"summary": summary, "flow": flow, "hours": hours}


@app.get("/api/earnings/{symbol}")
def api_earnings(symbol: str):
    """Get historical post-earnings stock performance — moon or tank predictor."""
    symbol = symbol.upper()

    # Check cache first
    cached = get_earnings_cache(symbol)
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return data

    # Fetch fresh data
    data = fetch_earnings_data(symbol)
    data["cached"] = False

    # Cache successful results
    if data.get("error") is None:
        set_earnings_cache(symbol, json.dumps(data))

    return data


@app.post("/api/scrape")
def api_scrape():
    """Trigger a scrape run. Returns pipeline stats."""
    stats = run_pipeline()
    return stats


# Serve frontend — must be after API routes
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Serve index.html for all non-API routes (SPA fallback)."""
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
