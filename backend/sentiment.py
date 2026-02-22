from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Custom WSB lexicon additions (word: sentiment score, -4.0 to +4.0)
WSB_LEXICON = {
    # Bullish
    "moon": 3.0,
    "mooning": 3.5,
    "moonshot": 3.0,
    "tendies": 2.5,
    "tendie": 2.5,
    "rocket": 2.5,
    "rockets": 2.5,
    "bullish": 3.0,
    "calls": 1.5,
    "squeeze": 2.0,
    "squeezing": 2.5,
    "diamond": 2.0,
    "diamonds": 2.0,
    "hodl": 2.0,
    "hodling": 2.0,
    "printer": 1.5,
    "brrrr": 2.0,
    "brrr": 2.0,
    "lambo": 2.5,
    "yolo": 1.5,
    "gains": 2.0,
    "gainz": 2.0,
    "rip": 2.0,
    "rippin": 2.5,
    "chad": 1.5,
    "alpha": 1.5,
    "undervalued": 2.0,
    "breakout": 2.0,
    "fomo": 1.0,
    "cheapies": 1.5,
    "loading": 1.0,
    "loaded": 1.5,
    "accumulate": 1.5,
    "accumulating": 1.5,
    "buy": 1.0,
    "buying": 1.0,
    "bought": 1.0,
    # Bearish
    "guh": -3.5,
    "bearish": -3.0,
    "puts": -1.5,
    "drill": -2.5,
    "drilling": -2.5,
    "tanking": -3.0,
    "tank": -2.5,
    "tanked": -3.0,
    "crash": -3.0,
    "crashed": -3.0,
    "crashing": -3.0,
    "dump": -2.5,
    "dumped": -2.5,
    "dumping": -3.0,
    "rugpull": -3.5,
    "rug": -2.0,
    "bagholder": -2.5,
    "bagholding": -2.5,
    "bags": -2.0,
    "loss": -2.0,
    "losses": -2.0,
    "dead": -2.5,
    "dying": -2.5,
    "rekt": -3.0,
    "wrecked": -2.5,
    "overvalued": -2.0,
    "scam": -3.0,
    "fraud": -3.0,
    "ponzi": -3.0,
    "bankruptcy": -3.5,
    "bankrupt": -3.5,
    "delisted": -3.0,
    "margin": -1.5,
    "overleveraged": -2.5,
    "sell": -1.0,
    "selling": -1.5,
    "sold": -1.0,
    "short": -1.0,
    "shorting": -1.5,
}

# Emoji sentiment
EMOJI_SCORES = {
    "🚀": 2.5,
    "🌙": 2.0,
    "💎": 2.0,
    "🙌": 1.5,
    "🦍": 1.0,
    "📈": 2.0,
    "💰": 1.5,
    "🤑": 1.5,
    "🔥": 1.5,
    "📉": -2.0,
    "💀": -2.0,
    "🤡": -2.5,
    "🗑️": -2.0,
    "😭": -1.5,
    "🐻": -1.5,
    "🐂": 1.5,
}

_analyzer = None


def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
        # Add WSB lexicon
        _analyzer.lexicon.update(WSB_LEXICON)
    return _analyzer


def score_sentiment(text):
    """Score text sentiment, returning compound score (-1.0 to 1.0).
    Incorporates VADER + WSB custom lexicon + emoji analysis.
    """
    if not text:
        return 0.0

    analyzer = get_analyzer()
    compound = analyzer.polarity_scores(text)["compound"]

    # Add emoji influence
    emoji_total = 0.0
    emoji_count = 0
    for emoji, score in EMOJI_SCORES.items():
        count = text.count(emoji)
        if count > 0:
            emoji_total += score * count
            emoji_count += count

    if emoji_count > 0:
        emoji_avg = emoji_total / emoji_count
        # Blend: 70% VADER, 30% emoji
        compound = 0.7 * compound + 0.3 * (emoji_avg / 4.0)  # normalize emoji to -1..1

    # Clamp to [-1, 1]
    return max(-1.0, min(1.0, compound))
