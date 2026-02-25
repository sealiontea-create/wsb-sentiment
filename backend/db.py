import sqlite3
import os
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "wsb.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            post_id TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            timestamp INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            title TEXT,
            author TEXT,
            upvotes INTEGER DEFAULT 0,
            UNIQUE(ticker, post_id)
        );
        CREATE INDEX IF NOT EXISTS idx_ticker ON mentions(ticker);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON mentions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_ticker_timestamp ON mentions(ticker, timestamp);

        CREATE TABLE IF NOT EXISTS options_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            strike REAL,
            option_type TEXT,
            expiry TEXT,
            expiry_category TEXT,
            raw_match TEXT,
            post_id TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            timestamp INTEGER NOT NULL,
            author TEXT,
            upvotes INTEGER DEFAULT 0,
            UNIQUE(ticker, strike, option_type, post_id)
        );
        CREATE INDEX IF NOT EXISTS idx_options_ticker ON options_flow(ticker);
        CREATE INDEX IF NOT EXISTS idx_options_timestamp ON options_flow(timestamp);

        CREATE TABLE IF NOT EXISTS earnings_cache (
            ticker TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            fetched_at INTEGER NOT NULL
        );
    """)
    conn.close()


def get_earnings_cache(ticker):
    """Return cached earnings JSON if < 24h old, else None."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT data, fetched_at FROM earnings_cache WHERE ticker = ?",
            (ticker.upper(),)
        ).fetchone()
        if row is None:
            return None
        age = int(datetime.now(timezone.utc).timestamp()) - row["fetched_at"]
        if age > 86400:  # 24 hours
            return None
        return row["data"]
    finally:
        conn.close()


def set_earnings_cache(ticker, data_json):
    """Upsert earnings cache row."""
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO earnings_cache (ticker, data, fetched_at)
               VALUES (?, ?, ?)
               ON CONFLICT(ticker) DO UPDATE SET data=excluded.data, fetched_at=excluded.fetched_at""",
            (ticker.upper(), data_json, int(datetime.now(timezone.utc).timestamp()))
        )
        conn.commit()
    finally:
        conn.close()


def insert_mention(ticker, post_id, sentiment_score, timestamp, source_type,
                   title=None, author=None, upvotes=0):
    conn = get_conn()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO mentions
               (ticker, post_id, sentiment_score, timestamp, source_type, title, author, upvotes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticker, post_id, sentiment_score, int(timestamp), source_type,
             title, author, upvotes)
        )
        conn.commit()
    finally:
        conn.close()


def insert_mentions_batch(rows):
    """Insert multiple mentions efficiently. rows = list of tuples matching insert_mention params."""
    conn = get_conn()
    try:
        conn.executemany(
            """INSERT OR IGNORE INTO mentions
               (ticker, post_id, sentiment_score, timestamp, source_type, title, author, upvotes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows
        )
        conn.commit()
        return conn.total_changes
    finally:
        conn.close()


def get_top_tickers(hours=24, limit=25):
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT
                ticker,
                COUNT(*) as mention_count,
                ROUND(AVG(sentiment_score), 4) as avg_sentiment,
                COUNT(DISTINCT author) as unique_authors,
                MAX(upvotes) as top_upvotes,
                MAX(timestamp) as latest_mention
            FROM mentions
            WHERE timestamp >= ?
            GROUP BY ticker
            HAVING COUNT(*) > 5
            ORDER BY mention_count DESC
            LIMIT ?
        """, (cutoff, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_ticker_detail(symbol, hours=24):
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT * FROM mentions
            WHERE ticker = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (symbol.upper(), cutoff)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_options_batch(rows):
    """Insert options flow. rows = list of tuples:
    (ticker, strike, option_type, expiry, expiry_category, raw_match, post_id, sentiment_score, timestamp, author, upvotes)
    """
    conn = get_conn()
    try:
        conn.executemany(
            """INSERT OR IGNORE INTO options_flow
               (ticker, strike, option_type, expiry, expiry_category, raw_match,
                post_id, sentiment_score, timestamp, author, upvotes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows
        )
        conn.commit()
        return conn.total_changes
    finally:
        conn.close()


def get_options_flow(hours=24, limit=50):
    """Get aggregated options flow — grouped by ticker + option_type."""
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT
                ticker,
                option_type,
                COUNT(*) as count,
                ROUND(AVG(strike), 2) as avg_strike,
                MIN(strike) as min_strike,
                MAX(strike) as max_strike,
                ROUND(AVG(sentiment_score), 4) as avg_sentiment,
                COUNT(DISTINCT author) as unique_authors,
                GROUP_CONCAT(DISTINCT expiry_category) as expiry_categories
            FROM options_flow
            WHERE timestamp >= ? AND option_type IS NOT NULL
            GROUP BY ticker, option_type
            ORDER BY count DESC
            LIMIT ?
        """, (cutoff, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_options_summary(hours=24):
    """Get high-level options stats."""
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    conn = get_conn()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM options_flow WHERE timestamp >= ?", (cutoff,)
        ).fetchone()[0]
        calls = conn.execute(
            "SELECT COUNT(*) FROM options_flow WHERE timestamp >= ? AND option_type='call'", (cutoff,)
        ).fetchone()[0]
        puts = conn.execute(
            "SELECT COUNT(*) FROM options_flow WHERE timestamp >= ? AND option_type='put'", (cutoff,)
        ).fetchone()[0]

        # Top bullish/bearish plays
        top_calls = conn.execute("""
            SELECT ticker, strike, expiry, expiry_category, raw_match, upvotes
            FROM options_flow
            WHERE timestamp >= ? AND option_type='call'
            ORDER BY upvotes DESC LIMIT 5
        """, (cutoff,)).fetchall()
        top_puts = conn.execute("""
            SELECT ticker, strike, expiry, expiry_category, raw_match, upvotes
            FROM options_flow
            WHERE timestamp >= ? AND option_type='put'
            ORDER BY upvotes DESC LIMIT 5
        """, (cutoff,)).fetchall()

        return {
            "total_options": total,
            "calls": calls,
            "puts": puts,
            "call_put_ratio": round(calls / max(puts, 1), 2),
            "top_calls": [dict(r) for r in top_calls],
            "top_puts": [dict(r) for r in top_puts],
        }
    finally:
        conn.close()


def get_db_stats():
    conn = get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM mentions").fetchone()[0]
        unique_tickers = conn.execute("SELECT COUNT(DISTINCT ticker) FROM mentions").fetchone()[0]
        latest_row = conn.execute("SELECT MAX(timestamp) FROM mentions").fetchone()[0]
        return {
            "total_mentions": total,
            "unique_tickers": unique_tickers,
            "latest_timestamp": latest_row,
        }
    finally:
        conn.close()
