"""Scrape r/wallstreetbets using Reddit's public JSON endpoints. No API key needed."""

import time
import urllib.request
import json

USER_AGENT = "wsb-sentiment-tracker/1.0"
BASE = "https://www.reddit.com/r/wallstreetbets"
REQUEST_DELAY = 1.2  # seconds between requests (respect rate limits)


def _fetch_json(url):
    """Fetch JSON from Reddit. Returns parsed dict or None on error."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[scraper] Error fetching {url}: {e}")
        return None


def _paginate_listing(path, limit):
    """Paginate through a Reddit listing endpoint. Returns list of post dicts."""
    seen_ids = set()
    posts = []
    after = None

    while len(posts) < limit:
        batch = min(100, limit - len(posts))
        url = f"{BASE}/{path}.json?limit={batch}&raw_json=1"
        if after:
            url += f"&after={after}"

        data = _fetch_json(url)
        if not data or "data" not in data:
            break

        children = data["data"]["children"]
        if not children:
            break

        for child in children:
            post = child["data"]
            if post["id"] in seen_ids:
                continue
            seen_ids.add(post["id"])
            posts.append({
                "id": post["id"],
                "title": post.get("title", ""),
                "selftext": post.get("selftext", ""),
                "author": post.get("author", "[deleted]"),
                "upvotes": post.get("score", 0),
                "created_utc": int(post.get("created_utc", 0)),
                "num_comments": post.get("num_comments", 0),
                "source_type": "post",
            })

        after = data["data"].get("after")
        if not after:
            break
        time.sleep(REQUEST_DELAY)

    return posts


def fetch_posts(limit_hot=200, limit_new=200, limit_rising=50):
    """Fetch hot + new + rising posts from r/wallstreetbets."""
    seen_ids = set()
    all_posts = []

    for listing, limit in [("hot", limit_hot), ("new", limit_new), ("rising", limit_rising)]:
        posts = _paginate_listing(listing, limit)
        for p in posts:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_posts.append(p)
        print(f"[scraper] {listing}: {len(posts)} fetched, {len(all_posts)} total unique")

    return all_posts


def _extract_comments_recursive(children, post_id, max_depth=3, depth=0):
    """Recursively extract comments from a comment tree."""
    comments = []
    for child in children:
        if child.get("kind") != "t1":
            continue
        c = child["data"]
        body = c.get("body", "")
        if body and body != "[deleted]" and body != "[removed]":
            comments.append({
                "id": f"{post_id}_{c['id']}",
                "title": body[:500],
                "selftext": "",
                "author": c.get("author", "[deleted]"),
                "upvotes": c.get("score", 0),
                "created_utc": int(c.get("created_utc", 0)),
                "source_type": "comment",
            })
        # Recurse into replies
        if depth < max_depth:
            replies = c.get("replies")
            if replies and isinstance(replies, dict):
                reply_children = replies.get("data", {}).get("children", [])
                comments.extend(
                    _extract_comments_recursive(reply_children, post_id, max_depth, depth + 1)
                )
    return comments


def fetch_comments(posts, top_n=50, comments_per_post=50):
    """Fetch comments from top N posts. Prioritizes discussion threads."""
    # Prioritize daily/weekly discussion threads — they have the most ticker mentions
    discussion_posts = [p for p in posts if _is_discussion_thread(p["title"])]
    other_posts = [p for p in posts if not _is_discussion_thread(p["title"])]
    other_posts.sort(key=lambda p: p["upvotes"], reverse=True)

    # Take all discussion threads + top N other posts
    targets = discussion_posts + other_posts[:max(0, top_n - len(discussion_posts))]
    comments = []

    for i, post_data in enumerate(targets):
        is_mega = _is_discussion_thread(post_data["title"])
        # Pull more comments from discussion threads
        limit = min(comments_per_post * 3, 150) if is_mega else comments_per_post
        tag = " [MEGATHREAD]" if is_mega else ""

        url = f"{BASE}/comments/{post_data['id']}.json?limit={limit}&sort=new&raw_json=1"
        data = _fetch_json(url)
        if not data or not isinstance(data, list) or len(data) < 2:
            time.sleep(REQUEST_DELAY)
            continue

        comment_children = data[1].get("data", {}).get("children", [])
        batch = _extract_comments_recursive(comment_children, post_data["id"])
        comments.extend(batch)

        if (i + 1) % 10 == 0 or is_mega:
            print(f"[scraper] Comments: {len(comments)} total ({i+1}/{len(targets)} posts){tag}")

        time.sleep(REQUEST_DELAY)

    print(f"[scraper] Fetched {len(comments)} comments from {len(targets)} posts")
    return comments


def _is_discussion_thread(title):
    """Check if a post is a daily/weekly discussion or earnings thread."""
    t = title.lower()
    keywords = ["daily discussion", "weekend discussion", "what are your moves",
                "earnings thread", "daily thread", "weekly discussion",
                "megathread", "moves tomorrow"]
    return any(k in t for k in keywords)
