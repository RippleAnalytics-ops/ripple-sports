#!/usr/bin/env python3
"""
collect.py — Pull stories from RSS feeds and save to issues/upcoming/raw_stories.json

Usage: python scripts/collect.py [--week-start YYYY-MM-DD]

By default collects the last 7 days. Run from the repo root.
"""

import json
import os
import sys
import hashlib
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

try:
    import feedparser
except ImportError:
    print("Run: pip install feedparser")
    sys.exit(1)

# ── Feed definitions ─────────────────────────────────────────────────────────
# Format: (league_name, emoji, category, feed_url)
FEEDS = [
    # US Sports — NFL
    ("NFL",   "🏈", "us-sports", "https://www.espn.com/espn/rss/nfl/news"),
    ("NFL",   "🏈", "us-sports", "https://www.nfl.com/rss/rsslanding?searchString=news"),
    # US Sports — NBA
    ("NBA",   "🏀", "us-sports", "https://www.espn.com/espn/rss/nba/news"),
    # US Sports — WNBA
    ("WNBA",  "🏀", "us-sports", "https://www.espn.com/espn/rss/wnba/news"),
    # US Sports — MLB
    ("MLB",   "⚾", "us-sports", "https://www.espn.com/espn/rss/mlb/news"),
    ("MLB",   "⚾", "us-sports", "https://www.mlb.com/feeds/news/rss.xml"),
    # US Sports — NHL
    ("NHL",   "🏒", "us-sports", "https://www.espn.com/espn/rss/nhl/news"),
    # Soccer
    ("Soccer","⚽", "soccer",    "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("Soccer","⚽", "soccer",    "https://www.skysports.com/rss/11095"),
    ("Soccer","⚽", "soccer",    "https://www.espn.com/espn/rss/soccer/news"),
    # Motorsport
    ("Formula 1","🏎️","motorsport","https://www.autosport.com/rss/feed/all"),
    ("NASCAR",   "🏁","motorsport","https://www.espn.com/espn/rss/rpm/news"),
    # Business & Media
    ("Business & Media","💼","general","https://frontofficesports.com/feed/"),
    ("Business & Media","💼","general","https://www.sportspro.com/feed/"),
    ("Business & Media","💼","general","https://www.cbssports.com/rss/headlines/"),
    # Business & Media — additional
    ("Business & Media","💼","general","https://sportico.com/feed/"),
    ("Business & Media","💼","general","https://boardroom.tv/feed/"),
    ("Business & Media","💼","general","https://awfulannouncing.com/feed"),
    ("Business & Media","💼","general","https://bleacherreport.com/articles/feed"),
]

# ── League keyword detection ─────────────────────────────────────────────────
# Helps re-classify stories that come from generic feeds
LEAGUE_KEYWORDS = {
    "NFL":          ["nfl", "quarterback", "touchdown", "super bowl", "draft pick", "wide receiver"],
    "NBA":          ["nba", "basketball", "playoffs", "three-pointer", "lakers", "celtics", "warriors"],
    "WNBA":         ["wnba", "women's basketball", "liberty", "fever", "sparks", "sky"],
    "MLB":          ["mlb", "baseball", "home run", "pitcher", "world series", "opening day"],
    "NHL":          ["nhl", "hockey", "stanley cup", "goalie", "power play"],
    "Formula 1":    ["formula 1", "f1", "grand prix", "hamilton", "verstappen", "ferrari", "red bull"],
    "NASCAR":       ["nascar", "daytona", "superspeedway", "kyle busch"],
    "Premier League":["premier league", "epl", "manchester", "arsenal", "chelsea", "liverpool", "tottenham"],
    "Real Madrid":  ["real madrid", "madrid", "bernabeu", "vinicius", "bellingham"],
    "MLS":          ["mls", "major league soccer", "inter miami", "lafc"],
    "NWSL":         ["nwsl", "women's soccer", "national women"],
    "UCL":          ["champions league", "ucl", "europa league"],
}

# ── Customer sections ─────────────────────────────────────────────────────────
# Stories mentioning these keywords get tagged as customer news (own section)
CUSTOMER_SECTIONS = {
    "LVF Serie A":    {"emoji": "🏐", "keywords": ["lvf", "lega volley", "legavolley", "italian volleyball", "serie a1 femminile", "serie a1 volleyball"]},
    "Enhanced Games": {"emoji": "⚡", "keywords": ["enhanced games"]},
    "HYROX":          {"emoji": "🏋️", "keywords": ["hyrox"]},
    "MXGP":           {"emoji": "🏍️", "keywords": ["mxgp", "motocross grand prix", "motocross gp", "mx2"]},
    "PGA Tour":       {"emoji": "⛳", "keywords": ["pga tour", "pga championship", "fedex cup"]},
    "FIFA World Cup": {"emoji": "🌍", "keywords": ["world cup 2026", "fifa world cup", "worldcup 2026", "world cup qualifier"]},
    "Sphere":         {"emoji": "🔮", "keywords": ["msg sphere", "sphere entertainment", "sphere las vegas", "sphere venue"]},
    "Parella Motorsports": {"emoji": "🏁", "keywords": ["parella", "parella motorsports", "racing america", "pmh"]},
}

# ── Tag suggestion rules ─────────────────────────────────────────────────────
TAG_KEYWORDS = {
    "🔥 Naming Rights": ["naming rights", "named after", "renamed", "name change", "new name", "rebranded", "title sponsor", "jersey sponsor", "kit sponsor", "shirt sponsor", "official partner", "official sponsor"],
    "🔥 Signing":  ["sign", "signed", "contract", "deal", "ink", "agrees"],
    "Trade":       ["trade", "traded", "acquire", "acquisition", "swap"],
    "Draft":       ["draft", "pick", "prospect", "combine", "pro day"],
    "Expansion":   ["expansion", "franchise", "new team"],
    "Playoffs":    ["playoff", "postseason", "championship", "final"],
    "Media":       ["broadcast", "streaming", "tv deal", "rights", "netflix", "apple", "amazon"],
    "Sponsors":    ["sponsor", "sponsorship", "partnership", "brand deal", "endorsement"],
    "Business":    ["revenue", "valuation", "sale", "sold", "billion", "million"],
    "Stadium":     ["stadium", "arena", "venue", "facility", "ground"],
    "Legal":       ["lawsuit", "court", "legal", "antitrust", "ruling", "settlement"],
    "Game":        ["win", "loss", "score", "recap", "highlights", "result"],
    "Contract":    ["extension", "renew", "option", "multi-year"],
    "Injury":      ["injury", "injured", "surgery", "return", "out for"],
    "Award":       ["award", "mvp", "player of", "coach of"],
    "Transfer":    ["transfer", "move", "join", "depart"],
}

def suggest_tag(text: str) -> tuple[str, bool]:
    """Return (tag, is_hot) based on headline text."""
    lower = text.lower()
    for tag, keywords in TAG_KEYWORDS.items():
        if any(k in lower for k in keywords):
            hot = tag.startswith("🔥") or any(w in lower for w in ["record", "historic", "first", "billion"])
            return tag.lstrip("🔥 "), hot
    return "News", False

def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url

def story_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:10]

def parse_date(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            import time
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None

def fetch_feed(league, emoji, category, url, cutoff_dt):
    """Fetch a single RSS feed and return list of story dicts."""
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "RippleSports/1.0"})
    except Exception as e:
        print(f"  ✗ {url}: {e}")
        return []

    stories = []
    for entry in feed.entries:
        pub = parse_date(entry)
        if pub and pub < cutoff_dt:
            continue  # too old

        title = entry.get("title", "").strip()
        link  = entry.get("link", "").strip()
        if not title or not link:
            continue

        # Try to detect a more specific league from generic feeds
        detected_league = league
        for lg, keywords in LEAGUE_KEYWORDS.items():
            if any(k in title.lower() for k in keywords):
                detected_league = lg
                break

        tag, hot = suggest_tag(title)

        stories.append({
            "id":       story_id(link),
            "league":   detected_league,
            "emoji":    emoji,
            "category": category,
            "text":     title,
            "summary":  entry.get("summary", "")[:200],
            "url":      link,
            "source":   extract_domain(link),
            "published": pub.isoformat() if pub else None,
            "suggested_tag": tag,
            "hot":      hot,
            "approved": None,  # null = not yet reviewed
        })
    return stories

def dedup(stories: list[dict]) -> list[dict]:
    seen_ids  = set()
    seen_urls = set()
    out = []
    for s in stories:
        if s["id"] in seen_ids or s["url"] in seen_urls:
            continue
        seen_ids.add(s["id"])
        seen_urls.add(s["url"])
        out.append(s)
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-start", default=None,
                        help="ISO date for week start, e.g. 2026-03-30. Default: 7 days ago.")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    if args.week_start:
        week_start = datetime.fromisoformat(args.week_start).replace(tzinfo=timezone.utc)
    else:
        week_start = now - timedelta(days=7)

    week_end = now

    print(f"Collecting stories from {week_start.date()} to {week_end.date()}")
    print(f"Fetching {len(FEEDS)} feeds...\n")

    all_stories = []
    for league, emoji, category, url in FEEDS:
        print(f"  → {league:20s} {url}")
        stories = fetch_feed(league, emoji, category, url, week_start)
        print(f"              {len(stories)} stories")
        all_stories.extend(stories)

    all_stories = dedup(all_stories)

    # ── Customer detection: scan every story for customer mentions ────────────
    customer_extras = []
    for s in all_stories:
        searchable = (s["text"] + " " + s.get("summary", "")).lower()
        for customer, meta in CUSTOMER_SECTIONS.items():
            if any(k in searchable for k in meta["keywords"]):
                import copy
                dupe = copy.copy(s)
                dupe["id"]       = s["id"] + "_cust"
                dupe["league"]   = customer
                dupe["emoji"]    = meta["emoji"]
                dupe["category"] = "customers"
                customer_extras.append(dupe)
                break  # assign to first matching customer only
    all_stories.extend(customer_extras)
    if customer_extras:
        print(f"\n  ★ {len(customer_extras)} stories flagged as customer news")

    # Sort newest first
    all_stories.sort(key=lambda s: s["published"] or "", reverse=True)

    out_dir = os.path.join("issues", "upcoming")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "raw_stories.json")

    output = {
        "collected_at": now.isoformat(),
        "week_start":   week_start.date().isoformat(),
        "week_end":     week_end.date().isoformat(),
        "total":        len(all_stories),
        "stories":      all_stories,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(all_stories)} unique stories saved to {out_path}")

if __name__ == "__main__":
    main()
