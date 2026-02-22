"""Extract options positions from WSB text.

Patterns matched:
  $NVDA 200c 3/27       → ticker=NVDA, strike=200, type=call, expiry=3/27
  SPY 680p 0DTE         → ticker=SPY, strike=680, type=put, expiry=0DTE
  UNH 295 calls friday  → ticker=UNH, strike=295, type=call, expiry=weekly
  AAPL 200p             → ticker=AAPL, strike=200, type=put, expiry=None
  SPX 0DTE              → ticker=SPX, strike=None, type=None, expiry=0DTE
"""

import re
from tickers import load_sec_tickers, BLOCKLIST

# Expiry keyword → normalized category
EXPIRY_KEYWORDS = {
    "0dte": "0DTE", "0DTE": "0DTE",
    "daily": "0DTE", "dailys": "0DTE", "dailies": "0DTE",
    "weekly": "weekly", "weeklys": "weekly", "weeklies": "weekly",
    "FD": "weekly", "FDs": "weekly", "fd": "weekly", "fds": "weekly",
    "monthly": "monthly", "monthlies": "monthly", "monthlys": "monthly",
    "leap": "LEAPS", "leaps": "LEAPS", "LEAP": "LEAPS", "LEAPS": "LEAPS",
    "friday": "weekly", "Friday": "weekly",
    "tomorrow": "0DTE", "tmrw": "0DTE",
    "next week": "weekly", "next friday": "weekly",
    "eow": "weekly", "EOW": "weekly",
    "eom": "monthly", "EOM": "monthly",
}

# Day-of-week names for expiry context
DAY_NAMES = {"monday", "tuesday", "wednesday", "thursday", "friday",
             "mon", "tue", "wed", "thu", "fri"}


def extract_options(text, known_tickers=None):
    """Extract options positions from text. Returns list of dicts.

    Each dict: {ticker, strike, option_type, expiry, expiry_category, raw_match}
    """
    if not text:
        return []

    sec_tickers = known_tickers or load_sec_tickers()
    options = []
    seen = set()

    # Pattern 1: TICKER STRIKEc/p [DATE]
    # e.g. "NVDA 200c 3/27", "SPY 680p", "$TSLA 250c 0DTE"
    for m in re.finditer(
        r'\$?([A-Z]{1,5})\s+(\d{1,5})[cCpP]\s*(?:(\d{1,2}/\d{1,2}(?:/\d{2,4})?))?',
        text
    ):
        ticker = m.group(1)
        if not _valid_ticker(ticker, sec_tickers):
            continue
        strike = float(m.group(2))
        opt_type = "call" if text[m.start(2) + len(m.group(2))].lower() == "c" else "put"
        expiry = m.group(3)
        expiry_cat = _categorize_expiry(expiry, text[m.end():m.end()+30])
        key = (ticker, strike, opt_type)
        if key not in seen:
            seen.add(key)
            options.append({
                "ticker": ticker,
                "strike": strike,
                "option_type": opt_type,
                "expiry": expiry,
                "expiry_category": expiry_cat,
                "raw_match": m.group(0).strip(),
            })

    # Pattern 2: TICKER STRIKE calls/puts [context]
    # e.g. "UNH 295 calls expiring Friday", "SPY 680 Puts"
    for m in re.finditer(
        r'\$?([A-Z]{1,5})\s+(\d{1,5})\s+(calls?|puts?)\b',
        text, re.IGNORECASE
    ):
        ticker = m.group(1)
        if not _valid_ticker(ticker, sec_tickers):
            continue
        strike = float(m.group(2))
        opt_type = "call" if m.group(3).lower().startswith("c") else "put"
        context_after = text[m.end():m.end()+40]
        expiry_cat = _categorize_expiry(None, context_after)
        key = (ticker, strike, opt_type)
        if key not in seen:
            seen.add(key)
            options.append({
                "ticker": ticker,
                "strike": strike,
                "option_type": opt_type,
                "expiry": None,
                "expiry_category": expiry_cat,
                "raw_match": m.group(0).strip(),
            })

    # Pattern 3: Standalone expiry keywords near tickers (for aggregate stats)
    # e.g. "buying SPY 0DTE", "NVDA weeklies"
    for m in re.finditer(
        r'\$?([A-Z]{1,5})\s+(0dte|0DTE|weeklies|weeklys|weekly|dailys?|dailies|FDs?|monthlies?|leaps?|LEAPS?)\b',
        text, re.IGNORECASE
    ):
        ticker = m.group(1)
        if not _valid_ticker(ticker, sec_tickers):
            continue
        keyword = m.group(2)
        expiry_cat = EXPIRY_KEYWORDS.get(keyword, EXPIRY_KEYWORDS.get(keyword.lower()))
        key = (ticker, None, None, expiry_cat)
        if key not in seen:
            seen.add(key)
            options.append({
                "ticker": ticker,
                "strike": None,
                "option_type": None,
                "expiry": keyword,
                "expiry_category": expiry_cat,
                "raw_match": m.group(0).strip(),
            })

    return options


def _valid_ticker(ticker, sec_tickers):
    """Check if a ticker is valid (not blocklisted, in SEC list)."""
    if ticker in BLOCKLIST:
        return False
    if sec_tickers and ticker not in sec_tickers:
        # Allow SPX, VIX, etc. — common options tickers not always in SEC list
        if ticker in {"SPX", "VIX", "NDX", "RUT", "DXY"}:
            return True
        return False
    return True


def _categorize_expiry(date_str, context=""):
    """Categorize expiry into 0DTE/weekly/monthly/LEAPS or None."""
    # Check explicit date
    if date_str:
        # Simple heuristic: if date is within ~7 days, weekly-ish
        return "dated"

    # Check context for keywords
    context_lower = context.lower()
    for keyword, category in EXPIRY_KEYWORDS.items():
        if keyword.lower() in context_lower:
            return category

    # Check for day names
    for day in DAY_NAMES:
        if day in context_lower:
            return "weekly"

    return None
