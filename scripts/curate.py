#!/usr/bin/env python3
"""
curate.py — Use Claude API to filter and format raw stories into newsletter-ready format.

Usage: python scripts/curate.py
Reads:  issues/upcoming/raw_stories.json
Writes: issues/upcoming/curated_stories.json

Requires: ANTHROPIC_API_KEY environment variable
          pip install anthropic
"""

import json
import os
import sys
import time

try:
    import anthropic
except ImportError:
    print("Run: pip install anthropic")
    sys.exit(1)

# ── How many stories to target per category ──────────────────────────────────
TARGET_PER_CATEGORY = {
    "us-sports": 50,
    "soccer":    20,
    "motorsport": 10,
    "general":   20,
    "customers": 20,  # customer-specific stories always prioritized
}

CURATION_PROMPT = """You are the editor of Ripple Sports Insights, a weekly sports business and on-field digest read by sports analytics project owners.

Your job: from the list of raw stories below, select the most newsworthy and curate them into newsletter format.

SELECTION RULES:
- TOP PRIORITY (never miss these): naming rights deals, stadium name changes, jersey/kit sponsorships, brand partnerships, new stadium announcements, venue naming deals, title sponsorships, league/team sponsor signings (e.g. "Arena renamed to X", "Brand becomes official partner of Y")
- HIGH PRIORITY: big signings/trades, media rights deals, expansion news, team sales/valuations, record-breaking contracts, major controversies, CBA/labor news
- NORMAL: notable game results, draft news, coaching changes, award news
- DEPRIORITIZE: minor game recaps, opinion pieces, injury updates for bench players, listicles, fantasy sports content
- Avoid duplicate topics (e.g. 3 articles about the same signing → pick best 1)
- Target totals: {target_counts}

FORMAT RULES for each selected story:
- "text": punchy headline, max 8 words, present tense, drop filler words ("the", "a")
  Examples: "Vikings sign Kyler Murray", "WNBA ratifies historic 7-year CBA", "Kraken push for NBA expansion"
- "tag": 1-2 word category tag (Signing, Trade, Media, Business, Draft, Expansion, Game, Legal, etc.)
  Prefix with 🔥 only for truly major stories (e.g. "🔥 Signing", "🔥 CBA")
- "hot": true only for the 5-8 biggest stories of the week (these go in the ticker)
- Keep original "url", "source", "league", "category", "emoji", "id"

IMPORTANT: Return ONLY a valid JSON array of selected story objects. No markdown, no explanation.

RAW STORIES:
{stories}
"""

def load_raw(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

MAX_STORIES_PER_CALL = 40  # stay within free-tier token limits
SLEEP_BETWEEN_CALLS  = 65  # seconds — reset the per-minute token window

def curate_category(client, stories: list[dict], category: str, target: int) -> list[dict]:
    """Send a batch of stories to Claude and get curated results.
    Pre-trims to MAX_STORIES_PER_CALL most recent stories to stay within token limits.
    """
    if not stories:
        return []

    # Sort by published date (newest first) and trim before sending
    sorted_stories = sorted(stories, key=lambda s: s.get("published") or "", reverse=True)
    trimmed = sorted_stories[:MAX_STORIES_PER_CALL]

    target_desc = f"{target} stories for the '{category}' category"
    stories_text = json.dumps(trimmed, indent=2, ensure_ascii=False)

    prompt = CURATION_PROMPT.format(
        target_counts=target_desc,
        stories=stories_text,
    )

    print(f"  Curating {len(trimmed)} (of {len(stories)}) → target {target} [{category}]...")
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw[:-3]

    try:
        curated = json.loads(raw)
        print(f"  ✓ Selected {len(curated)} stories")
        return curated
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        print("  Raw response:", raw[:300])
        return trimmed[:target]

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Get one at https://console.anthropic.com → API Keys")
        sys.exit(1)

    raw_path = os.path.join("issues", "upcoming", "raw_stories.json")
    if not os.path.exists(raw_path):
        print(f"Error: {raw_path} not found. Run collect.py first.")
        sys.exit(1)

    data = load_raw(raw_path)
    stories = data["stories"]
    print(f"Loaded {len(stories)} raw stories from {raw_path}\n")

    # Group by category
    by_cat: dict[str, list] = {}
    for s in stories:
        cat = s.get("category", "general")
        by_cat.setdefault(cat, []).append(s)

    client = anthropic.Anthropic(api_key=api_key)

    curated_all = []
    categories = list(by_cat.items())
    for i, (cat, cat_stories) in enumerate(categories):
        target = TARGET_PER_CATEGORY.get(cat, 5)
        curated = curate_category(client, cat_stories, cat, target)
        curated_all.extend(curated)
        if i < len(categories) - 1:
            print(f"  ⏳ Waiting {SLEEP_BETWEEN_CALLS}s to avoid rate limits...")
            time.sleep(SLEEP_BETWEEN_CALLS)

    # Sort by category then league for logical grouping
    CAT_ORDER = ["us-sports", "soccer", "motorsport", "general"]
    LEAGUE_ORDER = ["NFL", "WNBA", "NBA", "MLB", "NHL",
                    "Premier League", "Real Madrid", "MLS", "NWSL", "UCL",
                    "Formula 1", "NASCAR", "Business & Media"]

    def sort_key(s):
        cat = CAT_ORDER.index(s.get("category", "general")) if s.get("category") in CAT_ORDER else 99
        league = LEAGUE_ORDER.index(s.get("league", "")) if s.get("league") in LEAGUE_ORDER else 99
        return (cat, league)

    curated_all.sort(key=sort_key)

    out = {
        "week_start":  data["week_start"],
        "week_end":    data["week_end"],
        "curated_at":  __import__("datetime").datetime.utcnow().isoformat(),
        "total":       len(curated_all),
        "stories":     curated_all,
    }

    out_path = os.path.join("issues", "upcoming", "curated_stories.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(curated_all)} curated stories saved to {out_path}")
    print("Next step: open review/review.html in your browser to review and export the issue JSON.")

if __name__ == "__main__":
    main()
