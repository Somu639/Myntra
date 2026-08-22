"""Stage 1 — collect.py

Pulls raw text from four sources, normalizes each into a single schema, and
appends the results to ``raw_data.jsonl`` (one JSON object per line):

    {"source": str, "id": str, "text": str, "rating": float|None,
     "date": str|None, "meta": dict}

Sources
-------
- Google Play reviews for Myntra            (google-play-scraper, no auth)
- Apple App Store reviews for Myntra         (app-store-scraper / iTunes RSS)
- Reddit discussions                         (praw if creds exist, else public JSON + Pullpush)
- Fashion & shopping communities             (public subreddit JSON, no auth)
- Social media conversations                 (public Twitter syndication + Hacker News)
- YouTube comments from fashion haul videos  (youtube-comment-downloader)
- Product reviews & Q&A                      (Trustpilot public page JSON-LD)

Reddit credentials are optional. Without them we still collect via Reddit's
public JSON feed and Pullpush. If they are present, PRAW also pulls comments.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration — tweak these to change what gets collected.
# ---------------------------------------------------------------------------

MIN_TEXT_LEN = 15          # drop anything shorter than this (noise)
DEFAULT_LIMIT = 200        # items per query / video / subreddit search
SLEEP_SECONDS = 1.5        # polite pause between network calls
OUTPUT_FILE = "raw_data.jsonl"

# Google Play app IDs
GOOGLE_PLAY_APPS = {
    "google_play_myntra": "com.myntra.android",
}
GOOGLE_PLAY_LANG = "en"
GOOGLE_PLAY_COUNTRY = "in"

# Apple App Store (Myntra). app_id is the numeric id from the store URL.
APP_STORE_COUNTRY = "in"
APP_STORE_APP_NAME = "myntra"
APP_STORE_APP_ID = 907394059

# Reddit search: terms are OR-searched per subreddit (relevance-sorted).
# Mix of brand-anchored and shopping-behavior terms so we catch both "people
# talking about Myntra" and "people describing wishlist/return/fit behavior".
REDDIT_SUBREDDITS = [
    "IndianFashionAddicts", "IndianFashion", "IndianStreetwear",
    "india", "TwoXIndia", "onlineshopping", "IndianTeenagers",
]
# Broader fashion / shopping communities (posts about shopping behavior,
# not only the Myntra brand name).
FASHION_COMMUNITY_SUBS = [
    "IndianFashionAddicts", "IndianFashion", "IndianStreetwear",
    "femalefashionadvice", "malefashionadvice", "onlineshopping",
    "FrugalFemaleFashion", "plussize",
]
COMMUNITY_HINTS = (
    "myntra", "wishlist", "size chart", "return", "fit", "haul",
    "online shopping", "ethnic", "kurta", "dress", "sizing",
)
REDDIT_SEARCH_TERMS = [
    "myntra",
    "wishlist",
    "size chart",
    "returned it",
    "return refund",
    "fit sizing",
    "worth buying",
]
REDDIT_TOP_COMMENTS = 10   # top-level comments to keep per post
REDDIT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# YouTube fashion haul / review videos (full URLs).
YOUTUBE_VIDEOS = [
    "https://www.youtube.com/watch?v=I2fGkLwzebY",  # Myntra EORS haul
    "https://www.youtube.com/watch?v=1sixCZg3XTA",  # Myntra haul 2026
    "https://www.youtube.com/watch?v=V5HZKwdJMws",  # Myntra vacation wear
    "https://www.youtube.com/watch?v=cQ97tNTvrRM",  # cotton suit haul under 1000
    "https://www.youtube.com/watch?v=_Zxt4fB-NQ0",  # EORS 20 maxi dresses
]
YOUTUBE_MAX_COMMENTS = 200  # per video

# Public social timelines (Twitter syndication — no API key).
TWITTER_ACCOUNTS = ("myntra", "MyntraCares", "MyntraFashion")
TWITTER_HINTS = ("myntra", "order", "return", "refund", "delivery", "size", "fit")

# Product-review / Q&A destinations (public pages).
TRUSTPILOT_URL = "https://www.trustpilot.com/review/www.myntra.com"
HN_QUERY = "myntra"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def polite_sleep(seconds: float = SLEEP_SECONDS) -> None:
    """Pause between network calls so we don't hammer any single source."""
    time.sleep(seconds)


def to_iso(value) -> str | None:
    """Best-effort convert a date-ish value into an ISO 8601 string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        # Treat numbers as unix epoch seconds.
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        return value.strip() or None
    return str(value)


class Writer:
    """Appends normalized records to a JSONL file, filtering noise + duplicates."""

    def __init__(self, path: str):
        self.path = path
        self._fh = open(path, "a", encoding="utf-8")
        self._seen: set[tuple[str, str]] = set()
        self.kept = 0
        self.skipped_short = 0
        self.skipped_dupe = 0
        self._load_existing_ids()

    def _load_existing_ids(self) -> None:
        """Remember ids already on disk so re-runs don't create duplicates."""
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    key = (str(rec.get("source")), str(rec.get("id")))
                    self._seen.add(key)
        except OSError:
            pass

    def add(self, source: str, id_: str, text: str, rating=None,
            date=None, meta: dict | None = None) -> bool:
        """Normalize and write one record. Returns True if it was kept."""
        text = (text or "").strip()
        if len(text) < MIN_TEXT_LEN:
            self.skipped_short += 1
            return False

        key = (source, str(id_))
        if key in self._seen:
            self.skipped_dupe += 1
            return False
        self._seen.add(key)

        record = {
            "source": source,
            "id": str(id_),
            "text": text,
            "rating": rating,
            "date": to_iso(date),
            "meta": meta or {},
        }
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()
        self.kept += 1
        return True

    def close(self) -> None:
        self._fh.close()


# ---------------------------------------------------------------------------
# Source: Google Play reviews
# ---------------------------------------------------------------------------

def collect_google_play(writer: Writer, limit: int) -> None:
    try:
        from google_play_scraper import Sort, reviews
    except ImportError:
        print("[google_play] google-play-scraper not installed — "
              "run `pip install google-play-scraper`. Skipping.")
        return

    for source, app_id in GOOGLE_PLAY_APPS.items():
        print(f"[google_play] fetching up to {limit} reviews for {app_id} ...")
        try:
            result, _token = reviews(
                app_id,
                lang=GOOGLE_PLAY_LANG,
                country=GOOGLE_PLAY_COUNTRY,
                sort=Sort.NEWEST,
                count=limit,
            )
        except Exception as exc:  # noqa: BLE001 - keep other sources alive
            print(f"[google_play] error for {app_id}: {exc}")
            polite_sleep()
            continue

        for r in result:
            writer.add(
                source=source,
                id_=r.get("reviewId"),
                text=r.get("content"),
                rating=r.get("score"),
                date=r.get("at"),
                meta={
                    "app_id": app_id,
                    "user": r.get("userName"),
                    "thumbs_up": r.get("thumbsUpCount"),
                    "app_version": r.get("reviewCreatedVersion"),
                    "country": GOOGLE_PLAY_COUNTRY,
                },
            )
        print(f"[google_play] {source}: pulled {len(result)} raw reviews.")
        polite_sleep()


# ---------------------------------------------------------------------------
# Source: Apple App Store reviews
# ---------------------------------------------------------------------------

def collect_app_store(writer: Writer, limit: int) -> None:
    """Pull Myntra App Store reviews.

    Primary path uses app-store-scraper (per the brief). That library's token
    endpoint is frequently broken, so if it returns nothing we transparently
    fall back to Apple's public iTunes RSS reviews feed (JSON, no auth).
    """
    fetched = _app_store_via_scraper(limit)
    if fetched:
        for i, r in enumerate(fetched):
            raw_id = f"{r.get('userName', 'anon')}|{r.get('date')}"
            writer.add(
                source="app_store_myntra",
                id_=raw_id or f"app_store_{i}",
                text=r.get("review"),
                rating=r.get("rating"),
                date=r.get("date"),
                meta={
                    "app_id": APP_STORE_APP_ID,
                    "user": r.get("userName"),
                    "title": r.get("title"),
                    "developer_response": bool(r.get("developerResponse")),
                    "country": APP_STORE_COUNTRY,
                    "via": "app-store-scraper",
                },
            )
        print(f"[app_store] pulled {len(fetched)} raw reviews (scraper).")
        polite_sleep()
        return

    print("[app_store] scraper returned nothing — using iTunes RSS fallback.")
    _app_store_via_rss(writer, limit)


def _app_store_via_scraper(limit: int) -> list:
    try:
        from app_store_scraper import AppStore
    except ImportError:
        print("[app_store] app-store-scraper not installed — "
              "run `pip install app-store-scraper`. Trying RSS fallback.")
        return []

    print(f"[app_store] fetching up to {limit} reviews for "
          f"{APP_STORE_APP_NAME} ({APP_STORE_COUNTRY}) via scraper ...")
    try:
        app = AppStore(
            country=APP_STORE_COUNTRY,
            app_name=APP_STORE_APP_NAME,
            app_id=APP_STORE_APP_ID,
        )
        app.review(how_many=limit)  # sleeps internally between pages
        return app.reviews or []
    except Exception as exc:  # noqa: BLE001
        print(f"[app_store] scraper error: {exc}")
        return []


def _app_store_via_rss(writer: Writer, limit: int) -> None:
    """Apple's public customer-reviews RSS feed: 50/page, up to 10 pages."""
    try:
        import requests
    except ImportError:
        print("[app_store] requests not installed — cannot use RSS fallback.")
        return

    max_pages = min(10, (limit // 50) + 1)
    pulled = 0
    for page in range(1, max_pages + 1):
        url = (f"https://itunes.apple.com/{APP_STORE_COUNTRY}/rss/customerreviews/"
               f"id={APP_STORE_APP_ID}/sortBy=mostRecent/page={page}/json")
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                                timeout=20)
            resp.raise_for_status()
            entries = resp.json().get("feed", {}).get("entry", [])
        except Exception as exc:  # noqa: BLE001
            print(f"[app_store] RSS page {page} error: {exc}")
            break

        # The first entry on page 1 is app metadata (no 'im:rating') — skip it.
        review_entries = [e for e in entries if "im:rating" in e]
        if not review_entries:
            break

        for e in review_entries:
            if pulled >= limit:
                break
            writer.add(
                source="app_store_myntra",
                id_=e.get("id", {}).get("label"),
                text=e.get("content", {}).get("label"),
                rating=_safe_int(e.get("im:rating", {}).get("label")),
                date=e.get("updated", {}).get("label"),
                meta={
                    "app_id": APP_STORE_APP_ID,
                    "user": e.get("author", {}).get("name", {}).get("label"),
                    "title": e.get("title", {}).get("label"),
                    "app_version": e.get("im:version", {}).get("label"),
                    "country": APP_STORE_COUNTRY,
                    "via": "itunes-rss",
                },
            )
            pulled += 1
        if pulled >= limit:
            break
        polite_sleep()
    print(f"[app_store] pulled {pulled} raw reviews (RSS).")


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Source: Reddit (praw) — needs free credentials
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # .env support is optional; env vars still work.


def collect_reddit(writer: Writer, limit: int) -> None:
    _load_dotenv()
    _collect_reddit_public(writer, limit)

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", REDDIT_USER_AGENT)

    if not client_id or not client_secret:
        print("[reddit] no PRAW credentials — comments-via-API skipped "
              "(public JSON + Pullpush already ran).")
        return

    try:
        import praw
    except ImportError:
        print("[reddit] praw not installed — run `pip install praw`. Skipping.")
        return

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            check_for_async=False,
        )
        reddit.read_only = True
    except Exception as exc:  # noqa: BLE001
        print(f"[reddit] failed to init client: {exc}")
        return

    query = " OR ".join(f'"{term}"' for term in REDDIT_SEARCH_TERMS)
    per_sub = max(1, limit // max(1, len(REDDIT_SUBREDDITS)))

    for sub_name in REDDIT_SUBREDDITS:
        print(f"[reddit] searching r/{sub_name} for {REDDIT_SEARCH_TERMS} ...")
        try:
            submissions = reddit.subreddit(sub_name).search(
                query, sort="relevance", limit=per_sub
            )
            submissions = list(submissions)
        except Exception as exc:  # noqa: BLE001
            print(f"[reddit] search error in r/{sub_name}: {exc}")
            polite_sleep()
            continue

        for sub in submissions:
            body = (sub.title or "") + "\n" + (sub.selftext or "")
            writer.add(
                source="reddit",
                id_=f"post_{sub.id}",
                text=body,
                rating=sub.score,
                date=sub.created_utc,
                meta={
                    "kind": "post",
                    "subreddit": sub_name,
                    "title": sub.title,
                    "url": f"https://www.reddit.com{sub.permalink}",
                    "num_comments": sub.num_comments,
                },
            )

            # Pull a few top-level comments for extra voice-of-customer signal.
            try:
                sub.comments.replace_more(limit=0)
                top = sub.comments[:REDDIT_TOP_COMMENTS]
            except Exception as exc:  # noqa: BLE001
                print(f"[reddit] comment error on {sub.id}: {exc}")
                top = []

            for c in top:
                writer.add(
                    source="reddit",
                    id_=f"comment_{c.id}",
                    text=getattr(c, "body", ""),
                    rating=getattr(c, "score", None),
                    date=getattr(c, "created_utc", None),
                    meta={
                        "kind": "comment",
                        "subreddit": sub_name,
                        "post_id": sub.id,
                        "url": f"https://www.reddit.com{sub.permalink}",
                    },
                )
            polite_sleep()
        print(f"[reddit] r/{sub_name}: processed {len(submissions)} posts.")


# ---------------------------------------------------------------------------
# Source: YouTube comments
# ---------------------------------------------------------------------------

def collect_youtube(writer: Writer, limit: int) -> None:
    try:
        from youtube_comment_downloader import (SORT_BY_POPULAR,
                                                YoutubeCommentDownloader)
    except ImportError:
        print("[youtube] youtube-comment-downloader not installed — "
              "run `pip install youtube-comment-downloader`. Skipping.")
        return

    downloader = YoutubeCommentDownloader()
    max_per_video = min(limit, YOUTUBE_MAX_COMMENTS)

    for video in YOUTUBE_VIDEOS:
        print(f"[youtube] fetching up to {max_per_video} comments for {video} ...")
        count = 0
        try:
            stream = downloader.get_comments_from_url(
                video, sort_by=SORT_BY_POPULAR
            )
            for c in stream:
                if count >= max_per_video:
                    break
                writer.add(
                    source="youtube",
                    id_=c.get("cid"),
                    text=c.get("text"),
                    rating=None,  # comments have no rating
                    date=c.get("time_parsed"),  # epoch float if available
                    meta={
                        "video": video,
                        "author": c.get("author"),
                        "votes": c.get("votes"),
                        "time_text": c.get("time"),
                        "reply": c.get("reply"),
                    },
                )
                count += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[youtube] error for {video}: {exc}")
        print(f"[youtube] pulled {count} raw comments from {video}.")
        polite_sleep()


# ---------------------------------------------------------------------------
# HTTP helper (public, no-auth sources)
# ---------------------------------------------------------------------------

_BROWSER_UA = {
    "User-Agent": REDDIT_USER_AGENT,
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}


def _http_get(url: str, *, params=None, timeout: int = 25):
    import requests
    resp = requests.get(url, headers=_BROWSER_UA, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp


def _relevant(text: str, hints: tuple[str, ...]) -> bool:
    low = (text or "").lower()
    return any(h in low for h in hints)


# ---------------------------------------------------------------------------
# Source: Reddit public JSON + Pullpush (no credentials)
# ---------------------------------------------------------------------------

def _collect_reddit_public(writer: Writer, limit: int) -> int:
    """Read-only Reddit without OAuth: search.json, then Pullpush archive."""
    kept_before = writer.kept
    query = "myntra (wishlist OR return OR size OR fit OR haul)"
    per_sub = max(8, limit // max(1, len(REDDIT_SUBREDDITS)))

    for sub in REDDIT_SUBREDDITS:
        print(f"[reddit] public search r/{sub} ...")
        try:
            resp = _http_get(
                "https://arctic-shift.photon-reddit.com/api/posts/search",
                params={
                    "subreddit": sub,
                    "query": "myntra",
                    "limit": max(10, min(100, per_sub)),
                },
            )
            payload = resp.json()
            children = payload.get("data") or []
            children = [{"data": d} for d in children if isinstance(d, dict)]
        except Exception as exc:  # noqa: BLE001
            print(f"[reddit] public JSON r/{sub} failed: {exc}")
            children = []

        for child in children:
            data = child.get("data") or {}
            pid = data.get("id")
            if not pid:
                continue
            body = (data.get("title") or "") + "\n" + (data.get("selftext") or "")
            writer.add(
                source="reddit",
                id_=f"post_{pid}",
                text=body,
                rating=data.get("score"),
                date=data.get("created_utc"),
                meta={
                    "kind": "post",
                    "subreddit": data.get("subreddit") or sub,
                    "title": data.get("title"),
                    "url": f"https://www.reddit.com{data.get('permalink') or ''}",
                    "num_comments": data.get("num_comments"),
                    "via": "reddit-json",
                },
            )
        polite_sleep()

    print("[reddit] Pullpush archive search ...")
    try:
        resp = _http_get(
            "https://api.pullpush.io/reddit/search/submission/",
            params={"q": "myntra", "size": min(100, limit)},
        )
        posts = resp.json().get("data") or []
        if isinstance(posts, dict):
            posts = posts.get("children") or []
    except Exception as exc:  # noqa: BLE001
        print(f"[reddit] Pullpush failed: {exc}")
        posts = []

    for data in posts:
        if not isinstance(data, dict):
            continue
        # Pullpush sometimes wraps as {data: {...}}
        if "data" in data and isinstance(data["data"], dict) and "id" in data["data"]:
            data = data["data"]
        pid = data.get("id")
        if not pid:
            continue
        body = (data.get("title") or "") + "\n" + (data.get("selftext") or "")
        writer.add(
            source="reddit",
            id_=f"post_{pid}",
            text=body,
            rating=data.get("score"),
            date=data.get("created_utc"),
            meta={
                "kind": "post",
                "subreddit": data.get("subreddit"),
                "title": data.get("title"),
                "url": f"https://www.reddit.com{data.get('permalink') or ''}",
                "via": "pullpush",
            },
        )
    added = writer.kept - kept_before
    print(f"[reddit] public submissions added {added} items.")

    print("[reddit] Pullpush comments ...")
    try:
        resp = _http_get(
            "https://api.pullpush.io/reddit/search/comment/",
            params={"q": "myntra", "size": min(100, limit)},
        )
        comments = resp.json().get("data") or []
        if isinstance(comments, dict):
            comments = comments.get("children") or []
    except Exception as exc:  # noqa: BLE001
        print(f"[reddit] Pullpush comments failed: {exc}")
        comments = []

    c_kept = 0
    for data in comments:
        if not isinstance(data, dict):
            continue
        if "data" in data and isinstance(data["data"], dict) and "id" in data["data"]:
            data = data["data"]
        cid = data.get("id")
        body = data.get("body") or ""
        if not cid:
            continue
        if writer.add(
            source="reddit",
            id_=f"comment_{cid}",
            text=body,
            rating=data.get("score"),
            date=data.get("created_utc"),
            meta={
                "kind": "comment",
                "subreddit": data.get("subreddit"),
                "post_id": data.get("link_id"),
                "via": "pullpush-comment",
            },
        ):
            c_kept += 1
    print(f"[reddit] Pullpush comments kept {c_kept}.")
    return writer.kept - kept_before


# ---------------------------------------------------------------------------
# Source: fashion & shopping communities
# ---------------------------------------------------------------------------

def collect_communities(writer: Writer, limit: int) -> None:
    """Recent posts from fashion/shopping subreddits (public JSON, no auth)."""
    per = max(10, limit // max(1, len(FASHION_COMMUNITY_SUBS)))
    for sub in FASHION_COMMUNITY_SUBS:
        print(f"[communities] r/{sub} new posts ...")
        children = []
        try:
            resp = _http_get(
                "https://arctic-shift.photon-reddit.com/api/posts/search",
                params={"subreddit": sub, "limit": min(100, per)},
            )
            raw = resp.json().get("data") or []
            children = [{"data": d} for d in raw if isinstance(d, dict)]
        except Exception as exc:  # noqa: BLE001
            print(f"[communities] r/{sub} Arctic Shift failed: {exc}")
            children = []

        kept_here = 0
        for child in children:
            data = child.get("data") or {}
            pid = data.get("id")
            body = (data.get("title") or "") + "\n" + (data.get("selftext") or "")
            if not pid:
                continue
            if writer.add(
                source="fashion_community",
                id_=f"post_{pid}",
                text=body,
                rating=data.get("score"),
                date=data.get("created_utc"),
                meta={
                    "kind": "post",
                    "subreddit": data.get("subreddit") or sub,
                    "title": data.get("title"),
                    "url": f"https://www.reddit.com{data.get('permalink') or ''}",
                    "via": "reddit-json",
                },
            ):
                kept_here += 1
        print(f"[communities] r/{sub}: kept {kept_here}.")
        polite_sleep()


# ---------------------------------------------------------------------------
# Source: social media (Twitter syndication) + other public conversations (HN)
# ---------------------------------------------------------------------------

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def collect_social(writer: Writer, limit: int) -> None:
    """Public Twitter profile syndication + Hacker News search (no API keys)."""
    per_acct = max(5, limit // max(1, len(TWITTER_ACCOUNTS)))
    for account in TWITTER_ACCOUNTS:
        url = (
            "https://syndication.twitter.com/srv/timeline-profile/"
            f"screen-name/{account}"
        )
        print(f"[social] twitter @{account} ...")
        count = 0
        try:
            html = _http_get(url).text
            match = _NEXT_DATA_RE.search(html)
            payload = json.loads(match.group(1)) if match else {}
            tweets: list[dict] = []
            seen: set[str] = set()

            def walk(obj) -> None:
                if isinstance(obj, dict):
                    text = obj.get("full_text") or obj.get("text")
                    tid = obj.get("id_str") or (
                        str(obj.get("id")) if obj.get("id") is not None else ""
                    )
                    if text and tid and tid not in seen:
                        seen.add(tid)
                        tweets.append(obj)
                    for v in obj.values():
                        if isinstance(v, (dict, list)):
                            walk(v)
                elif isinstance(obj, list):
                    for item in obj:
                        walk(item)

            walk(payload)
            for tw in tweets:
                if count >= per_acct:
                    break
                text = tw.get("full_text") or tw.get("text") or ""
                if not _relevant(text, TWITTER_HINTS):
                    continue
                tid = tw.get("id_str") or tw.get("id")
                user = (tw.get("user") or {}).get("screen_name") or account
                if writer.add(
                    source="social_twitter",
                    id_=str(tid),
                    text=text,
                    rating=tw.get("favorite_count"),
                    date=tw.get("created_at"),
                    meta={
                        "account": user,
                        "via": "twitter-syndication",
                        "url": f"https://twitter.com/{user}/status/{tid}",
                    },
                ):
                    count += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[social] twitter @{account} failed: {exc}")
        print(f"[social] @{account}: kept {count}.")
        polite_sleep()

    print("[social] Hacker News (Algolia) ...")
    hn_kept = 0
    try:
        resp = _http_get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": HN_QUERY, "hitsPerPage": min(50, limit)},
        )
        for hit in resp.json().get("hits") or []:
            hid = hit.get("objectID")
            text = (hit.get("title") or "") + "\n" + (hit.get("story_text") or hit.get("comment_text") or "")
            if not hid or not _relevant(text, ("myntra", "fashion", "shopping")):
                continue
            if writer.add(
                source="other_public",
                id_=f"hn_{hid}",
                text=text,
                rating=hit.get("points"),
                date=hit.get("created_at"),
                meta={
                    "via": "hn-algolia",
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hid}",
                    "author": hit.get("author"),
                },
            ):
                hn_kept += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[social] HN failed: {exc}")
    print(f"[social] HN kept {hn_kept}.")


# ---------------------------------------------------------------------------
# Source: product reviews & Q&A (Trustpilot)
# ---------------------------------------------------------------------------

def collect_product_reviews(writer: Writer, limit: int) -> None:
    """Public product reviews (Sitejabber JSON-LD) and Q&A-style HN comments."""
    print("[product] Sitejabber myntra.com ...")
    kept = 0
    try:
        html = _http_get("https://www.sitejabber.com/reviews/myntra.com").text
        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            reviews = data.get("review") if isinstance(data, dict) else None
            if not reviews:
                continue
            if isinstance(reviews, dict):
                reviews = [reviews]
            for rev in reviews:
                if kept >= limit:
                    break
                body = (rev.get("headline") or "") + "\n" + (rev.get("reviewBody") or "")
                rid = rev.get("url") or rev.get("headline") or f"sj_{kept}"
                rating = None
                rr = rev.get("reviewRating") or {}
                if isinstance(rr, dict):
                    rating = _safe_int(rr.get("ratingValue"))
                author = rev.get("author") or {}
                if writer.add(
                    source="product_review",
                    id_=str(rid),
                    text=body.strip(),
                    rating=rating,
                    date=rev.get("datePublished"),
                    meta={
                        "via": "sitejabber-jsonld",
                        "url": rev.get("url") or "https://www.sitejabber.com/reviews/myntra.com",
                        "author": author.get("name") if isinstance(author, dict) else author,
                    },
                ):
                    kept += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[product] Sitejabber failed: {exc}")
    print(f"[product] Sitejabber kept {kept}.")

    print("[product] Trustpilot fallback ...")
    try:
        html = _http_get(TRUSTPILOT_URL).text
        tp = 0
        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            reviews = data.get("review") if isinstance(data, dict) else None
            if not reviews:
                continue
            if isinstance(reviews, dict):
                reviews = [reviews]
            for rev in reviews:
                body = (rev.get("headline") or "") + "\n" + (rev.get("reviewBody") or "")
                rid = rev.get("@id") or rev.get("url") or f"tp_{tp}"
                rr = rev.get("reviewRating") or {}
                if writer.add(
                    source="product_review",
                    id_=str(rid),
                    text=body.strip(),
                    rating=_safe_int(rr.get("ratingValue") if isinstance(rr, dict) else None),
                    date=rev.get("datePublished"),
                    meta={"via": "trustpilot-jsonld", "url": TRUSTPILOT_URL},
                ):
                    tp += 1
        print(f"[product] Trustpilot kept {tp}.")
    except Exception as exc:  # noqa: BLE001
        print(f"[product] Trustpilot skipped: {exc}")

    print("[product] HN comments as public Q&A ...")
    qa = 0
    try:
        resp = _http_get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "myntra", "tags": "comment", "hitsPerPage": min(50, limit)},
        )
        for hit in resp.json().get("hits") or []:
            hid = hit.get("objectID")
            text = hit.get("comment_text") or ""
            if not hid or not text:
                continue
            if writer.add(
                source="product_qa",
                id_=f"hn_comment_{hid}",
                text=text,
                rating=hit.get("points"),
                date=hit.get("created_at"),
                meta={
                    "via": "hn-algolia-comment",
                    "url": f"https://news.ycombinator.com/item?id={hid}",
                    "author": hit.get("author"),
                    "story": hit.get("story_title"),
                },
            ):
                qa += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[product] HN Q&A failed: {exc}")
    print(f"[product] HN Q&A kept {qa}.")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

COLLECTORS = {
    "play": collect_google_play,
    "ios": collect_app_store,
    "reddit": collect_reddit,
    "communities": collect_communities,
    "social": collect_social,
    "youtube": collect_youtube,
    "product": collect_product_reviews,
}


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 1 raw text collector.")
    parser.add_argument(
        "--sources", nargs="+", choices=list(COLLECTORS) + ["all"],
        default=["all"], help="Which sources to pull (default: all).",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT,
        help=f"Max items per query (default: {DEFAULT_LIMIT}).",
    )
    parser.add_argument(
        "--out", default=OUTPUT_FILE,
        help=f"Output JSONL path (default: {OUTPUT_FILE}).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    sources = list(COLLECTORS) if "all" in args.sources else args.sources

    print(f"=== Stage 1 collect — sources={sources}, limit={args.limit}, "
          f"out={args.out} ===")

    writer = Writer(args.out)
    try:
        for name in sources:
            print(f"\n--- {name} ---")
            try:
                COLLECTORS[name](writer, args.limit)
            except Exception as exc:  # noqa: BLE001 - never let one source kill the run
                print(f"[{name}] unexpected error: {exc}")
    finally:
        writer.close()

    print("\n=== Done ===")
    print(f"kept={writer.kept}  skipped_short={writer.skipped_short}  "
          f"skipped_dupe={writer.skipped_dupe}")
    print(f"Appended to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
