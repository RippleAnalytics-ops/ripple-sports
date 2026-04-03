# Ripple Sports Newsletter — Weekly Workflow

## Every time you want to publish a new issue:

### Step 1 — Go to repo
```bash
cd ~/Documents/ripple-sports
```

### Step 2 — Collect stories from RSS feeds
```bash
python3 scripts/collect.py
```
Pulls 300+ stories from ESPN, BBC, Front Office Sports, etc.

### Step 3 — Curate with AI (takes ~4 min due to rate limits)
```bash
python3 scripts/curate.py
```
Requires ANTHROPIC_API_KEY to be set. If it's not:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Step 4 — Review stories in browser
```bash
open review/review.html
```
- Click **Choose File** → select `issues/upcoming/curated_stories.json`
- Set issue number + date range
- Approve/drop/edit stories, mark 🔥 hot ones for the ticker
- Click title's **↗** to open the original article
- Click **Export Issue JSON** → **Download**
- Save file as `issues/issue-XX.json`

### Step 5 — Generate the HTML
```bash
python3 scripts/generate.py issues/issue-16.json
```
Outputs `issue-16.html` and updates `index.html` automatically.

### Step 6 — Preview & publish
```bash
open issue-16.html   # preview in browser
```
Then push to GitHub:
```bash
git add .
git commit -m "Add Issue 16"
git push
```
GitHub Pages publishes automatically in ~30 seconds.

---

## Curation priorities (what Claude looks for)
- 🔥 TOP: Naming rights, stadium renames, jersey/kit sponsors, brand partnerships
- ⬆ HIGH: Signings, trades, media rights, expansion, team sales
- ➡ NORMAL: Game results, draft news, coaching changes
- ⬇ SKIP: Opinion pieces, injury bench players, fantasy content

## Story targets per issue
- US Sports: up to 50
- Soccer: up to 20
- Motorsport: up to 10
- Business & Media: up to 20

## Files
- `scripts/collect.py` — RSS feed collector
- `scripts/curate.py`  — AI story curation
- `scripts/generate.py`— JSON → HTML renderer
- `review/review.html` — Editorial review UI
- `issues/upcoming/`   — Raw + curated story JSON (auto-generated)
- `issues/`            — Saved issue JSON files
