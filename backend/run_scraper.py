"""Pipeline: scrape WSB → extract tickers → score sentiment → extract options → save to DB."""

import time
from db import init_db, insert_mentions_batch, insert_options_batch
from scraper import fetch_posts, fetch_comments
from tickers import extract_tickers
from sentiment import score_sentiment
from options import extract_options


def run_pipeline():
    """Run the full scrape-analyze-store pipeline. Returns stats dict."""
    start = time.time()
    init_db()

    # 1. Scrape
    print("[pipeline] Fetching posts...")
    posts = fetch_posts()
    print("[pipeline] Fetching comments...")
    comments = fetch_comments(posts)
    all_items = posts + comments

    # 2. Extract tickers + score sentiment → build DB rows
    mention_rows = []
    option_rows = []

    for item in all_items:
        text = f"{item['title']} {item.get('selftext', '')}"
        tickers = extract_tickers(text)
        sentiment = score_sentiment(text)

        # Ticker mentions
        if tickers:
            for ticker in tickers:
                mention_rows.append((
                    ticker,
                    item["id"],
                    sentiment,
                    item["created_utc"],
                    item["source_type"],
                    item["title"][:200],
                    item["author"],
                    item["upvotes"],
                ))

        # Options extraction (runs on all text, not just ticker-matched)
        opts = extract_options(text)
        for opt in opts:
            option_rows.append((
                opt["ticker"],
                opt["strike"],
                opt["option_type"],
                opt["expiry"],
                opt["expiry_category"],
                opt["raw_match"],
                item["id"],
                sentiment,
                item["created_utc"],
                item["author"],
                item["upvotes"],
            ))

    # 3. Save
    mentions_inserted = insert_mentions_batch(mention_rows)
    options_inserted = insert_options_batch(option_rows)
    elapsed = round(time.time() - start, 1)

    stats = {
        "posts_fetched": len(posts),
        "comments_fetched": len(comments),
        "mentions_found": len(mention_rows),
        "mentions_inserted": mentions_inserted,
        "options_found": len(option_rows),
        "options_inserted": options_inserted,
        "elapsed_seconds": elapsed,
    }
    print(f"[pipeline] Done in {elapsed}s — {len(mention_rows)} mentions ({mentions_inserted} new), "
          f"{len(option_rows)} options ({options_inserted} new)")
    return stats


if __name__ == "__main__":
    run_pipeline()
