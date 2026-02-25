"""Earnings Oracle — historical post-earnings stock performance analysis.

Uses yfinance to fetch earnings dates + daily prices, calculates
moon/tank probabilities based on price moves around earnings announcements.
Entertainment only — not financial advice.
"""

import statistics
import json
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Tickers that don't have earnings — roast them WSB style
_ROASTS = {
    # Index ETFs
    "SPY": "SPY doesn't have earnings you absolute walnut. It's 500 companies in a trenchcoat 🧥",
    "QQQ": "QQQ is an ETF, not a company. It doesn't report earnings. Sir this is a Wendy's 🍔",
    "IWM": "IWM is 2000 small caps duct-taped together. No earnings call, just vibes 🦧",
    "DIA": "DIA tracks the Dow. 30 boomers in a basket. No earnings to see here 👴",
    "VOO": "VOO is literally just SPY wearing a Vanguard sweater vest. No earnings 🧶",
    "VTI": "VTI is the entire US stock market. ALL of it. You want earnings for... everything? 🌎",
    # Leveraged / inverse
    "TQQQ": "TQQQ is a 3x leveraged ETF. It doesn't have earnings, it has a gambling addiction 🎰",
    "SQQQ": "SQQQ is a bear ETF. No earnings. It just sits there and decays like your portfolio 💀",
    "UVXY": "UVXY tracks fear itself. Fear doesn't file 10-Qs 👻",
    "SPXL": "SPXL is leveraged SPY. No earnings. Just amplified regret 📉📉📉",
    "SOXL": "SOXL is a leveraged semiconductor ETF. Semiconductors have earnings. SOXL does not. Stay in school 📚",
    "SOXS": "SOXS is an inverse semiconductor ETF. It exists purely to destroy wealth. No earnings 🔥",
    # Commodities
    "GLD": "GLD is literally gold bars in a vault. Gold doesn't do earnings calls 🥇",
    "SLV": "SLV is silver. A shiny rock. Rocks don't have quarterly reports 🪨",
    "USO": "USO tracks oil. Oil comes from the ground, not from a CEO on CNBC 🛢️",
    "AGQ": "AGQ is 2x leveraged silver. Double the rock, still no earnings 🪨🪨",
    # Crypto-adjacent
    "BTC": "BTC is Bitcoin. Satoshi doesn't do earnings calls. Probably dead anyway 💀",
    "BITO": "BITO is a Bitcoin futures ETF. Crypto doesn't have earnings you degenerate 🤡",
    "MARA": None,  # MARA actually has earnings, don't roast
    # VIX products
    "VIX": "VIX is a fear index. You can't even buy it directly. What are you doing here 🤦",
    "VXX": "VXX tracks VIX futures. No earnings. Just existential dread in ETN form 😰",
    # Bonds
    "TLT": "TLT is a bond ETF. Bonds don't have earnings. They barely have a pulse 💤",
    "HYG": "HYG is junk bonds in ETF form. No earnings. Just prayers 🙏",
}

# Pre-fetched earnings dates cache (built locally, committed to repo)
_PREFETCH_PATH = os.path.join(os.path.dirname(__file__), "data", "earnings_prefetch.json")
_prefetch_cache = None


def _load_prefetch():
    """Load pre-fetched earnings dates from JSON file."""
    global _prefetch_cache
    if _prefetch_cache is not None:
        return _prefetch_cache
    if os.path.exists(_PREFETCH_PATH):
        with open(_PREFETCH_PATH, "r") as f:
            _prefetch_cache = json.load(f)
    else:
        _prefetch_cache = {}
    return _prefetch_cache


def prefetch_earnings(symbols):
    """Pre-fetch COMPLETE earnings data (dates + prices + computed metrics) for a list of symbols.

    Run this locally (where Yahoo works fully) to build the cache file.
    The cache file gets committed to the repo and deployed to Render.
    On Render, the API just serves this JSON directly — zero Yahoo calls needed.
    """
    cache = _load_prefetch()
    for sym in symbols:
        sym = sym.upper()
        print(f"[prefetch] {sym}...", end=" ", flush=True)
        try:
            result = fetch_earnings_data(sym)
            if result.get("error"):
                print(f"skip: {result['error']}")
                continue
            # Store the full computed result — ready to serve as-is
            cache[sym] = result
            print(f"{result['events']} events, moon={result['moon_pct']}%")
        except Exception as e:
            print(f"error: {e}")

    os.makedirs(os.path.dirname(_PREFETCH_PATH), exist_ok=True)
    with open(_PREFETCH_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"\n[prefetch] Saved {len(cache)} tickers to {_PREFETCH_PATH}")
    return cache


def _get_earnings_dates_robust(ticker, symbol):
    """Try multiple strategies to get earnings dates from yfinance.

    Returns a list of dicts with 'date' (datetime), 'eps_estimate', 'eps_actual' keys,
    or an empty list on failure.
    """
    results = []

    # Strategy 0: Pre-fetched cache (built locally, works everywhere)
    prefetch = _load_prefetch()
    if symbol.upper() in prefetch:
        for entry in prefetch[symbol.upper()]:
            d = datetime.strptime(entry["date"], "%Y-%m-%d")
            if d > datetime.now():
                continue
            results.append({
                "date": d,
                "eps_estimate": entry.get("eps_estimate"),
                "eps_actual": entry.get("eps_actual"),
            })
        if results:
            return results

    # Strategy 1: get_earnings_dates (scrapes HTML — works locally, often blocked on cloud)
    try:
        ed = ticker.get_earnings_dates(limit=16)
        if ed is not None and not ed.empty:
            for date_idx, row in ed.iterrows():
                d = date_idx.tz_localize(None) if date_idx.tzinfo else date_idx
                if d > datetime.now():
                    continue
                results.append({
                    "date": d,
                    "eps_estimate": _safe_float(row.get("EPS Estimate")),
                    "eps_actual": _safe_float(row.get("Reported EPS")),
                })
            if results:
                return results
    except Exception:
        pass

    # Strategy 2: quarterly_income_stmt column dates (API-based, works from servers)
    try:
        stmt = ticker.quarterly_income_stmt
        if stmt is not None and not stmt.empty:
            for col_date in stmt.columns:
                d = pd.Timestamp(col_date)
                d = d.tz_localize(None) if d.tzinfo else d
                d = d.to_pydatetime()
                if d > datetime.now():
                    continue
                eps_actual = None
                for row_name in ["Basic EPS", "Diluted EPS"]:
                    if row_name in stmt.index:
                        eps_actual = _safe_float(stmt.loc[row_name, col_date])
                        if eps_actual is not None:
                            break
                results.append({
                    "date": d,
                    "eps_estimate": None,
                    "eps_actual": eps_actual,
                })
            if results:
                return results
    except Exception:
        pass

    return results


def fetch_earnings_data(symbol):
    """Fetch earnings history + price data, calculate moon/tank metrics.

    Returns a dict with all metrics, history events, and commentary.
    On failure returns {"error": "message"}.
    """
    # Roast ETFs/indexes/crypto that don't have earnings
    roast = _ROASTS.get(symbol.upper())
    if roast is not None:
        return {"error": roast}

    # Check prefetch for full pre-computed result first
    prefetch = _load_prefetch()
    if symbol.upper() in prefetch:
        cached = prefetch[symbol.upper()]
        # If it's a full result (has 'moon_pct'), serve it directly
        if "moon_pct" in cached:
            return cached

    try:
        ticker = yf.Ticker(symbol.upper())

        # Get earnings dates via multi-strategy approach
        earnings_list = _get_earnings_dates_robust(ticker, symbol)
        if not earnings_list:
            return {"error": f"No earnings data available for {symbol.upper()}"}

        # Get 5 years of daily price data
        try:
            hist = ticker.history(period="5y")
        except Exception as e:
            return {"error": f"Could not fetch price history for {symbol.upper()}: {e}"}

        if hist is None or hist.empty:
            return {"error": f"No price history available for {symbol.upper()}"}

        # Process each earnings event
        events = []
        for earn in earnings_list:
            earn_date = earn["date"]
            eps_estimate = earn["eps_estimate"]
            eps_actual = earn["eps_actual"]

            # Calculate EPS surprise
            surprise_pct = None
            if eps_estimate is not None and eps_actual is not None and eps_estimate != 0:
                surprise_pct = round((eps_actual - eps_estimate) / abs(eps_estimate) * 100, 2)

            # Find price before and after earnings
            price_before = _get_price_around_date(hist, earn_date, "before")
            price_after = _get_price_around_date(hist, earn_date, "after")

            if price_before is None or price_after is None:
                continue

            move_pct = round((price_after - price_before) / price_before * 100, 2)
            classification = _classify_move(move_pct)

            events.append({
                "date": earn_date.strftime("%Y-%m-%d"),
                "eps_estimate": eps_estimate,
                "eps_actual": eps_actual,
                "surprise_pct": surprise_pct,
                "price_before": round(price_before, 2),
                "price_after": round(price_after, 2),
                "move_pct": move_pct,
                "classification": classification,
            })

        if not events:
            return {"error": f"Could not calculate earnings moves for {symbol.upper()} — insufficient price data around earnings dates"}

        # Sort by date descending (most recent first)
        events.sort(key=lambda e: e["date"], reverse=True)

        # Calculate aggregate metrics
        moves = [e["move_pct"] for e in events]
        total = len(events)

        moon_events = sum(1 for e in events if e["classification"] in ("MOON", "PUMP"))
        tank_events = sum(1 for e in events if e["classification"] in ("DIP", "TANK"))
        flat_events = sum(1 for e in events if e["classification"] == "FLAT")

        moon_pct = round(moon_events / total * 100, 1)
        tank_pct = round(tank_events / total * 100, 1)
        flat_pct = round(flat_events / total * 100, 1)
        avg_move = round(statistics.mean(moves), 2)
        max_moon = round(max(moves), 2)
        max_tank = round(min(moves), 2)
        volatility = round(statistics.stdev(moves), 2) if len(moves) > 1 else 0.0

        # Streak calculation
        streak, streak_direction = _calculate_streak(events)

        # GUH score
        guh_score = _calculate_guh_score(volatility, avg_move)

        # Commentary
        commentary = _generate_commentary(moon_pct, tank_pct, volatility, avg_move, streak, streak_direction)

        # Years covered
        dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in events]
        years_covered = round((max(dates) - min(dates)).days / 365.25, 1) if len(dates) > 1 else 0.0

        return {
            "symbol": symbol.upper(),
            "events": total,
            "years_covered": years_covered,
            "moon_pct": moon_pct,
            "tank_pct": tank_pct,
            "flat_pct": flat_pct,
            "avg_move": avg_move,
            "max_moon": max_moon,
            "max_tank": max_tank,
            "volatility": volatility,
            "streak": streak,
            "streak_direction": streak_direction,
            "guh_score": guh_score,
            "commentary": commentary,
            "history": events,
            "error": None,
        }

    except Exception as e:
        return {"error": f"Failed to fetch data for {symbol.upper()}: {str(e)}"}


def _safe_float(val):
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        import math
        f = float(val)
        if math.isnan(f):
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None


def _get_price_around_date(prices_df, target_date, direction):
    """Find the closest trading day's close price before or after target_date.

    direction: 'before' = last trading day on or before target
               'after' = first trading day after target
    """
    # Normalize the prices index to tz-naive for comparison
    prices_index = prices_df.index.tz_localize(None) if prices_df.index.tzinfo else prices_df.index

    if direction == "before":
        # Last trading day on or before the day before earnings
        before_date = target_date - timedelta(days=1)
        mask = prices_index <= before_date
        if not mask.any():
            return None
        idx = prices_index[mask][-1]
        return float(prices_df.loc[prices_df.index[prices_index == idx][0], "Close"])
    else:
        # First trading day after earnings
        after_date = target_date + timedelta(days=1)
        mask = prices_index >= after_date
        if not mask.any():
            return None
        idx = prices_index[mask][0]
        return float(prices_df.loc[prices_df.index[prices_index == idx][0], "Close"])


def _classify_move(pct):
    """Classify a percentage move into WSB categories."""
    if pct > 5:
        return "MOON"
    elif pct > 2:
        return "PUMP"
    elif pct >= -2:
        return "FLAT"
    elif pct >= -5:
        return "DIP"
    else:
        return "TANK"


def _calculate_streak(events):
    """Calculate current consecutive direction streak from most recent events."""
    if not events:
        return 0, "flat"

    streak = 0
    direction = None

    for event in events:  # already sorted most recent first
        move = event["move_pct"]
        if move > 2:
            event_dir = "moon"
        elif move < -2:
            event_dir = "tank"
        else:
            event_dir = "flat"

        if direction is None:
            direction = event_dir
            streak = 1
        elif event_dir == direction:
            streak += 1
        else:
            break

    return streak, direction or "flat"


def _calculate_guh_score(volatility, avg_move):
    """Calculate GUH Score (0-10) — how much of a casino is this stock around earnings."""
    return round(min(10, volatility * 1.5 + abs(avg_move) * 0.5), 1)


def _generate_commentary(moon_pct, tank_pct, volatility, avg_move, streak, streak_direction):
    """Generate fun WSB-themed commentary based on the data."""
    lines = []

    # Primary verdict
    if moon_pct >= 70:
        lines.append("This thing PRINTS after earnings 🚀🚀🚀")
    elif tank_pct >= 70:
        lines.append("GUH. This stock hates earnings season 💀")
    elif volatility > 8 and abs(avg_move) < 2:
        lines.append("Pure casino. Flip a coin 🎰")
    elif abs(moon_pct - tank_pct) < 15:
        lines.append("50/50 — your wife's boyfriend has better odds 🎲")
    elif moon_pct >= 55:
        lines.append("Leans bullish after earnings. Not a sure thing though 📈")
    elif tank_pct >= 55:
        lines.append("Tends to dump after earnings. Puts gang might eat 🐻")
    else:
        lines.append("Mixed bag — could go either way 🤷")

    # Streak commentary
    if streak >= 3 and streak_direction == "moon":
        lines.append(f"{streak} moons in a row — streak is HOT 🔥")
    elif streak >= 3 and streak_direction == "tank":
        lines.append(f"{streak} tanks in a row — when does it stop 📉")

    # Volatility commentary
    if volatility > 10:
        lines.append("Absolute rollercoaster around earnings. Strap in 🎢")
    elif volatility < 2:
        lines.append("Barely moves on earnings. Theta gang wins again 🐌")

    return " ".join(lines)
