import re
import os
import json
import urllib.request

CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "sec_tickers.json")

# Common English words, WSB slang, and abbreviations that look like tickers
BLOCKLIST = {
    # WSB slang
    "AI", "DD", "YOLO", "HODL", "FOMO", "FD", "TLDR", "IMO", "IMHO", "WSB",
    "MOASS", "APE", "APES", "ROPE", "GUH", "BULL", "BEAR", "DIP", "DIPS",
    "ATH", "ATL", "OTM", "ITM", "DTM", "IV", "DTE", "FD", "LEAP", "LEAPS",
    "PT", "TP", "SL", "EOD", "EOW", "EOM", "EOY", "YTD", "QE", "GDP",
    "CPI", "PPI", "NFP", "FOMC", "IPO", "SEC", "ETF", "ETN", "CEO",
    "CFO", "COO", "CTO", "CMO", "CIO", "VP", "SVP", "EVP", "BOD",
    # Common words that match ticker patterns
    "ALL", "ARE", "AND", "ANY", "BIG", "BIT", "BUT", "BUY", "CAN", "CAR",
    "DAY", "DID", "DO", "EAR", "EAT", "END", "ERA", "FAT", "FAN", "FAR",
    "FED", "FEW", "FOR", "FUN", "GAP", "GET", "GOD", "GOT", "GAS", "HAS",
    "HAD", "HIT", "HOT", "HOW", "ICE", "ILL", "ITS", "JOB", "KEY", "LET",
    "LOT", "LOW", "MAN", "MAP", "MAY", "MEN", "MET", "MOM", "NET", "NEW",
    "NOT", "NOW", "NUT", "ODD", "OFF", "OLD", "ONE", "OUR", "OUT", "OWN",
    "PAY", "PER", "PIT", "PLZ", "POP", "PUT", "RAN", "RAW", "RED", "RIP",
    "RUN", "SAD", "SAT", "SAW", "SAY", "SET", "SHE", "SIT", "SIX", "SKY",
    "SOS", "SUN", "TAN", "TAX", "THE", "TIP", "TOP", "TOO", "TWO", "USE",
    "VAN", "WAR", "WAY", "WAS", "WHO", "WHY", "WIN", "WON", "YES", "YET",
    "YOU", "ZIP",
    # Longer common words
    "ALSO", "BACK", "BEEN", "BEST", "CALL", "CASH", "COME", "CORE", "COST",
    "DATA", "DEAL", "DEEP", "DOWN", "EACH", "EASY", "EDIT", "EVEN", "EVER",
    "FACE", "FACT", "FAST", "FEEL", "FILL", "FIND", "FIRE", "FLAT", "FLIP",
    "FLOW", "FOOD", "FREE", "FROM", "FULL", "FUND", "GAIN", "GAME", "GAVE",
    "GLAD", "GOES", "GOLD", "GONE", "GOOD", "GRAB", "GREW", "GROW", "HALF",
    "HAND", "HANG", "HARD", "HATE", "HAVE", "HEAD", "HEAR", "HELD", "HELP",
    "HERE", "HIGH", "HOLD", "HOME", "HOPE", "HUGE", "IDEA", "INTO", "JUST",
    "KEEP", "KILL", "KIND", "KNEW", "KNOW", "LACK", "LAND", "LAST", "LATE",
    "LEAD", "LEFT", "LEND", "LESS", "LIFE", "LIKE", "LINE", "LINK", "LIVE",
    "LONG", "LOOK", "LOSE", "LOSS", "LOST", "LOVE", "LUCK", "MADE", "MAIN",
    "MAKE", "MANY", "MARK", "MEAN", "MINE", "MISS", "MODE", "MORE", "MOON",
    "MOST", "MOVE", "MUCH", "MUST", "NEAR", "NEED", "NEXT", "NICE", "NONE",
    "NORM", "NOTE", "ONLY", "OPEN", "ONCE", "OVER", "PAGE", "PAID", "PART",
    "PASS", "PAST", "PATH", "PICK", "PLAN", "PLAY", "PLUS", "POLL", "POOR",
    "POST", "PULL", "PUMP", "PURE", "PUSH", "PUTS", "RATE", "READ", "REAL",
    "RENT", "REST", "RICH", "RIDE", "RISE", "RISK", "ROAD", "ROCK", "ROLL",
    "RULE", "RUNS", "RUSH", "SAFE", "SAID", "SALE", "SAME", "SAVE", "SELL",
    "SEND", "SHOP", "SHOT", "SHOW", "SHUT", "SIDE", "SIGN", "SIZE", "SLOW",
    "SOLD", "SOME", "SOON", "SORT", "STAY", "STEP", "STOP", "SURE", "SWAP",
    "TAKE", "TALK", "TANK", "TEAM", "TELL", "TEST", "THAN", "THAT", "THEM",
    "THEN", "THEY", "THIS", "TICK", "TIME", "TOLD", "TOOK", "TOPS", "TURN",
    "TYPE", "UNIT", "UPON", "USED", "VERY", "VOTE", "WAIT", "WAKE", "WALK",
    "WALL", "WANT", "WEAK", "WEEK", "WELL", "WENT", "WERE", "WHAT", "WHEN",
    "WHOM", "WIDE", "WILL", "WISH", "WITH", "WORD", "WORK", "YEAR", "YOUR",
    "ZERO",
    # Reddit/internet slang
    "EDIT", "TLDR", "LMAO", "LMFAO", "STFU", "GTFO", "IDGAF", "ROFL",
    "NSFW", "IIRC", "TIL", "ELI5", "AFAIK",
    # Financial terms
    "CALL", "PUTS", "LONG", "SHORT", "GAIN", "LOSS", "SELL", "HOLD",
    "PUMP", "DUMP", "FUND", "BOND", "DEBT", "LOAN", "RATE", "RISK",
    "CASH", "FEES", "COST", "FREE", "PAID", "SAVE", "SPEND",
}

_sec_tickers = None


def load_sec_tickers():
    """Load valid ticker symbols from SEC EDGAR (cached locally)."""
    global _sec_tickers
    if _sec_tickers is not None:
        return _sec_tickers

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            _sec_tickers = set(json.load(f))
        return _sec_tickers

    # Download from SEC EDGAR
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "wsb-sentiment-tracker admin@example.com"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        tickers = {entry["ticker"].upper() for entry in data.values()}
        with open(CACHE_PATH, "w") as f:
            json.dump(sorted(tickers), f)
        _sec_tickers = tickers
        print(f"[tickers] Cached {len(tickers)} SEC tickers")
        return _sec_tickers
    except Exception as e:
        print(f"[tickers] Warning: Could not fetch SEC tickers: {e}")
        _sec_tickers = set()
        return _sec_tickers


def extract_tickers(text):
    """Extract stock tickers from text. Returns set of uppercase ticker strings."""
    if not text:
        return set()

    found = set()
    sec_tickers = load_sec_tickers()

    # Pattern 1: $TICKER — high confidence, skip blocklist
    dollar_pattern = re.findall(r'\$([A-Z]{1,5})\b', text.upper())
    for t in dollar_pattern:
        if len(t) >= 2 and (not sec_tickers or t in sec_tickers):
            found.add(t)

    # Pattern 2: Bare uppercase words — filtered against blocklist + SEC list
    bare_pattern = re.findall(r'\b([A-Z]{2,5})\b', text)
    for t in bare_pattern:
        if t in BLOCKLIST:
            continue
        if sec_tickers and t not in sec_tickers:
            continue
        found.add(t)

    return found
