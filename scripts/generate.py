#!/usr/bin/env python3
"""
generate.py — Render a Ripple Sports newsletter issue from a JSON data file.

Usage: python scripts/generate.py issues/issue-16.json
Outputs: issue-16.html (in repo root)
Also updates: index.html (adds new issue card)

Run from the repo root.
"""

import json
import os
import re
import sys
from html import escape
from datetime import datetime

# ── Season auto-detection ─────────────────────────────────────────────────────
SEASON_MONTHS = {
    "NFL":            [9,10,11,12,1,2],
    "WNBA":           [5,6,7,8,9,10],
    "NBA":            [10,11,12,1,2,3,4,5,6],
    "MLB":            [4,5,6,7,8,9,10],
    "NHL":            [10,11,12,1,2,3,4,5,6],
    "Premier League": [8,9,10,11,12,1,2,3,4,5],
    "Real Madrid":    [8,9,10,11,12,1,2,3,4,5],
    "MLS":            [2,3,4,5,6,7,8,9,10,11],
    "NWSL":           [3,4,5,6,7,8,9,10,11],
    "UCL":            [9,10,11,12,1,2,3,4,5],
    "Formula 1":      [3,4,5,6,7,8,9,10,11],
    "NASCAR":         [2,3,4,5,6,7,8,9,10,11],
    "LVF Serie A":    [9,10,11,12,1,2,3,4,5],
    "PGA Tour":       [1,2,3,4,5,6,7,8],
    "FIFA World Cup": [6,7],
    "MXGP":           [3,4,5,6,7,8,9,10],
    "HYROX":          [1,2,3,4,5,9,10,11,12],
    "Enhanced Games": [1,2,3,4,5,6,7,8,9,10,11,12],
}

def get_season(league: str) -> tuple:
    month = datetime.now().month
    months = SEASON_MONTHS.get(league)
    if months is None:
        return ("off", "This Week")
    return ("in", "In-season") if month in months else ("off", "Off-season")

# ── HTML helpers ─────────────────────────────────────────────────────────────

def esc(s: str) -> str:
    return escape(str(s), quote=True)

def domain(url: str) -> str:
    """Extract display domain from URL."""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url

def render_ticker(items: list[dict]) -> str:
    parts = []
    for t in items:
        cls = "ticker-item hot" if t.get("hot") else "ticker-item"
        parts.append(
            f'    <a href="{esc(t["url"])}" target="_blank" rel="noopener" class="{cls}">'
            f'<span class="t-dot"></span>{esc(t["text"])}</a>'
        )
    # Duplicate for seamless loop
    all_items = parts + parts
    return "\n".join(all_items)

def render_story(s: dict) -> str:
    tag = s.get("tag", "News")
    if s.get("hot") and not tag.startswith("🔥"):
        tag = f"🔥 {tag}"
    src = s.get("source") or domain(s.get("url", ""))
    summary = s.get("summary", "")
    data_attrs = f' data-source="{esc(src)}"'
    if summary:
        data_attrs += f' data-summary="{esc(summary)}"'
    return (
        f'          <a href="{esc(s["url"])}" target="_blank" rel="noopener" class="item"{data_attrs}>'
        f'<span class="item-tag">{esc(tag)}</span>'
        f'<div class="item-body">'
        f'<div class="item-text">{esc(s["text"])}</div>'
        f'<div class="item-source">{esc(src)}</div>'
        f'</div><span class="item-arrow">↗</span></a>'
    )

def render_card(card: dict) -> str:
    season, season_label = get_season(card.get("league", ""))
    season_cls = season
    emoji = card.get("emoji", "")
    league = esc(card.get("league", ""))
    cat = esc(card.get("category", "general"))
    stories_html = "\n".join(render_story(s) for s in card.get("stories", []))
    return f"""      <!-- {card.get('league', '')} -->
      <section class="card" data-cat="{cat}">
        <div class="card-head"><div class="league-label"><span class="league-emoji">{emoji}</span><span class="league-text">{league}</span></div><div class="season-tag {season_cls}">{esc(season_label)}</div></div>
        <div class="card-items">
{stories_html}
        </div>
      </section>"""

def render_editor_pick(pick: dict) -> str:
    tag = pick.get("tag", "Story")
    if pick.get("hot") and not tag.startswith("🔥"):
        tag = f"🔥 {tag}"
    src = pick.get("source") or domain(pick.get("url", ""))
    return f"""      <!-- EDITOR'S PICK -->
      <a href="{esc(pick['url'])}" target="_blank" rel="noopener" class="editor-pick">
        <div class="editor-pick-label">⭐ Editor's Pick</div>
        <div class="editor-pick-headline">{esc(pick['text'])}</div>
        <div class="editor-pick-meta">
          <span class="editor-pick-tag">{esc(tag)}</span>
          <span class="editor-pick-source">{esc(src)}</span>
          <span class="editor-pick-arrow">↗</span>
        </div>
      </a>"""

# ── Full HTML template ────────────────────────────────────────────────────────

CSS = """:root{--bg:#0a0a0f;--surface:#111118;--surface2:#16161f;--border:rgba(255,255,255,0.07);--border-hover:rgba(255,255,255,0.16);--ink:#f0eff5;--ink2:#8a899a;--ink3:#3e3d50;--g1:#8C52FF;--g2:#2BA8FF;--g3:#F7C948;--grad:linear-gradient(135deg,var(--g1),var(--g2),var(--g3));--grad-text:linear-gradient(-45deg,var(--g1),var(--g2),var(--g3),var(--g2));--radius:14px;--shadow-hover:0 16px 40px rgba(0,0,0,.45)}
[data-theme="light"]{--bg:#c4c3d4;--surface:#d6d4e8;--surface2:#cac8dc;--border:rgba(0,0,0,0.11);--border-hover:rgba(140,82,255,0.35);--ink:#0a0a0f;--ink2:#3a3950;--ink3:#7878a0}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:'DM Sans',sans-serif;font-size:14px;line-height:1.6;min-height:100vh;overflow-x:hidden;transition:background .35s,color .35s}
body::after{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");opacity:.025;pointer-events:none;z-index:9999}
.shell{max-width:1280px;margin:0 auto;padding:0 32px}
header{padding:56px 0 0;position:relative;overflow:hidden}
.ripple-stage{position:absolute;inset:0;pointer-events:none;z-index:0;overflow:hidden}
@keyframes rippleOut{0%{transform:scale(0);opacity:.7}100%{transform:scale(5);opacity:0}}
.rring{position:absolute;border-radius:50%;border:1.5px solid color-mix(in srgb,var(--g2) 45%,transparent)}
.rring:nth-child(1){width:24px;height:24px;top:18%;left:6%;animation:rippleOut 3.2s cubic-bezier(.4,0,.2,1) infinite 0s}
.rring:nth-child(2){width:32px;height:32px;top:55%;right:10%;animation:rippleOut 3.2s cubic-bezier(.4,0,.2,1) infinite 1.1s}
.rring:nth-child(3){width:20px;height:20px;bottom:14%;left:22%;animation:rippleOut 3.2s cubic-bezier(.4,0,.2,1) infinite 2.1s}
.rring:nth-child(4){width:28px;height:28px;top:30%;right:28%;animation:rippleOut 3.2s cubic-bezier(.4,0,.2,1) infinite .6s;border-color:color-mix(in srgb,var(--g1) 35%,transparent)}
.header-inner{position:relative;z-index:2;display:grid;grid-template-columns:1fr auto;align-items:end;gap:24px;padding-bottom:28px;border-bottom:1px solid var(--border)}
.brand-eyebrow{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.18em;text-transform:uppercase;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:8px}
@keyframes shimmer{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.brand-title{font-family:'Bebas Neue',sans-serif;font-size:clamp(56px,9vw,108px);line-height:.9;letter-spacing:.02em;background:var(--grad-text);background-size:300% 300%;animation:shimmer 6s ease infinite;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;display:block}
.brand-title-sub{font-family:'Bebas Neue',sans-serif;font-size:clamp(20px,3vw,34px);letter-spacing:.22em;color:transparent;-webkit-text-stroke:1px var(--ink2);display:block;margin-top:-2px}
.brand-sub{font-size:12px;color:var(--ink2);font-weight:300;margin-top:10px;letter-spacing:.04em}
.header-meta{display:flex;flex-direction:column;align-items:flex-end;gap:10px;padding-bottom:4px}
.theme-btn{background:var(--surface);border:1px solid var(--border);color:var(--ink2);width:40px;height:40px;border-radius:10px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:17px;position:relative;transition:border-color .2s,transform .2s,box-shadow .2s;z-index:1}
.theme-btn::before{content:'';position:absolute;inset:-4px;border-radius:14px;background:radial-gradient(circle at 30% 30%,color-mix(in srgb,var(--g1) 25%,transparent),transparent 60%),radial-gradient(circle at 70% 70%,color-mix(in srgb,var(--g2) 20%,transparent),transparent 60%);opacity:0;filter:blur(4px);z-index:-1;transition:opacity .2s}
.theme-btn:hover::before{opacity:1}.theme-btn:hover{transform:translateY(-2px) scale(1.04);border-color:var(--border-hover);box-shadow:0 4px 16px color-mix(in srgb,var(--g1) 20%,transparent);color:var(--ink)}
.ticker-wrap{overflow:hidden;border-bottom:1px solid var(--border);background:var(--surface);padding:9px 0;position:relative}
.ticker-wrap::before,.ticker-wrap::after{content:'';position:absolute;top:0;bottom:0;width:72px;z-index:2;pointer-events:none}
.ticker-wrap::before{left:0;background:linear-gradient(to right,var(--surface),transparent)}
.ticker-wrap::after{right:0;background:linear-gradient(to left,var(--surface),transparent)}
.ticker-track{display:flex;width:max-content;animation:ticker 140s linear infinite}
.ticker-track:hover{animation-play-state:paused}
@keyframes ticker{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.ticker-item{display:flex;align-items:center;gap:10px;padding:0 28px;white-space:nowrap;font-family:'DM Mono',monospace;font-size:10px;color:var(--ink2);border-right:1px solid var(--border);text-decoration:none;transition:color .15s;cursor:pointer}
.ticker-item:hover{color:var(--ink)}.ticker-item.hot:hover .t-dot{box-shadow:0 0 8px color-mix(in srgb,var(--g1) 80%,transparent)}
.t-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;background:var(--g2)}
.ticker-item.hot .t-dot{background:var(--g1);box-shadow:0 0 6px color-mix(in srgb,var(--g1) 60%,transparent)}
.controls-bar{position:sticky;top:0;z-index:100;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:12px 0;transition:background .35s}
.controls-inner{max-width:1280px;margin:0 auto;padding:0 32px;display:flex;align-items:center;gap:14px}
.search-box{flex-shrink:0;width:260px;position:relative}
.search-box input{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:9px;color:var(--ink);font-family:'DM Sans',sans-serif;font-size:13px;padding:8px 14px 8px 36px;outline:none;transition:border-color .2s,box-shadow .2s}
.search-box input::placeholder{color:var(--ink3)}.search-box input:focus{border-color:var(--g1);box-shadow:0 0 0 3px color-mix(in srgb,var(--g1) 14%,transparent)}
.search-icon{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--ink3);font-size:14px;pointer-events:none}
.chips{display:flex;gap:6px;overflow-x:auto;flex:1;scrollbar-width:none;align-items:center}.chips::-webkit-scrollbar{display:none}
.chip{flex-shrink:0;padding:6px 15px;border-radius:100px;border:1px solid var(--border);background:transparent;color:var(--ink2);font-family:'DM Sans',sans-serif;font-size:12px;font-weight:500;cursor:pointer;letter-spacing:.02em;white-space:nowrap;position:relative;transition:color .2s,border-color .2s,transform .2s,box-shadow .2s;z-index:1;overflow:hidden}
.chip::before{content:'';position:absolute;inset:-1px;border-radius:100px;background:var(--grad);opacity:0;z-index:-1;transition:opacity .2s}
.chip:hover{color:var(--ink);border-color:var(--border-hover);transform:translateY(-1px)}
.chip.active{color:#fff;border-color:transparent;background:transparent;box-shadow:0 2px 14px color-mix(in srgb,var(--g1) 35%,transparent)}.chip.active::before{opacity:1}
.main{display:grid;grid-template-columns:minmax(0,1fr) 218px;gap:28px;padding:36px 0 80px;align-items:start}
.feed{display:grid;grid-template-columns:repeat(auto-fill,minmax(296px,1fr));gap:18px;align-items:start}
@keyframes fadeUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;animation:fadeUp .55s cubic-bezier(.2,.9,.2,1) both;position:relative;transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease}
.card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.35);border-color:rgba(255,255,255,.13);overflow:visible}
.card:nth-child(1){animation-delay:.04s}.card:nth-child(2){animation-delay:.09s}.card:nth-child(3){animation-delay:.14s}.card:nth-child(4){animation-delay:.19s}.card:nth-child(5){animation-delay:.24s}.card:nth-child(6){animation-delay:.29s}.card:nth-child(7){animation-delay:.34s}.card:nth-child(8){animation-delay:.39s}.card:nth-child(9){animation-delay:.44s}.card:nth-child(10){animation-delay:.49s}.card:nth-child(11){animation-delay:.54s}
.card-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 12px 16px;border-bottom:1px solid var(--border);background:var(--surface2);overflow:visible}
.league-label{font-family:'Bebas Neue',sans-serif;font-size:19px;letter-spacing:.04em;line-height:1.3;padding-top:2px;display:flex;align-items:center;gap:8px}
.league-emoji{font-style:normal;-webkit-text-fill-color:initial;background:none;font-size:20px;line-height:1;flex-shrink:0}
.league-text{background:var(--grad-text);background-size:300% 300%;animation:shimmer 8s ease infinite;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.season-tag{font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:.1em;padding:3px 7px;border-radius:3px;border:1px solid;white-space:nowrap}
.season-tag.in{color:var(--g2);border-color:color-mix(in srgb,var(--g2) 30%,transparent)}.season-tag.off{color:var(--ink3);border-color:var(--border)}
.card-items{display:flex;flex-direction:column;padding:8px;gap:2px;flex:1;position:relative;overflow:visible}
@keyframes borderSpin{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.item{display:flex;align-items:flex-start;gap:10px;padding:10px 12px 10px 16px;border-radius:8px;text-decoration:none;color:inherit;position:relative;background:var(--surface);border:1.5px solid transparent;transition:box-shadow .18s,transform .18s;z-index:0}
.item::after{content:'';position:absolute;inset:-1.5px;border-radius:9px;background:linear-gradient(var(--angle,0deg),var(--g1),var(--g2),var(--g3),var(--g2),var(--g1));background-size:300% 300%;-webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);-webkit-mask-composite:xor;mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);mask-composite:exclude;padding:1.5px;opacity:.25;pointer-events:none;animation:borderSpin 2.5s linear infinite paused}
.item:hover{transform:translateY(-3px) scale(1.02);box-shadow:0 8px 24px rgba(0,0,0,.45);border-color:transparent}
.item:hover::after{opacity:1;animation-play-state:running}.item:hover .item-text{color:var(--ink)}.item:hover .item-source{color:var(--g2)}.item:hover .item-arrow{opacity:1}
.item-tag{flex-shrink:0;font-family:'DM Mono',monospace;font-size:9px;font-weight:500;text-transform:uppercase;letter-spacing:.08em;padding:3px 8px;border-radius:3px;background:color-mix(in srgb,var(--g1) 10%,transparent);color:var(--g2);border:1px solid color-mix(in srgb,var(--g2) 25%,transparent);margin-top:1px;white-space:nowrap;display:inline-block}
.item-body{flex:1;min-width:0}.item-text{font-size:13px;font-weight:500;color:var(--ink2);line-height:1.4;transition:color .15s}
.item-source{font-family:'DM Mono',monospace;font-size:10px;color:var(--ink3);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.item-arrow{flex-shrink:0;font-size:12px;opacity:0;color:var(--ink2);transition:opacity .15s;margin-top:2px}
.sidebar{position:sticky;top:78px;display:flex;flex-direction:column;gap:18px}
.sidebar-block{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;transition:border-color .2s}.sidebar-block:hover{border-color:var(--border-hover)}
.sidebar-head{display:flex;align-items:center;padding:11px 14px;border-bottom:1px solid var(--border);background:var(--surface2)}
.sidebar-title{font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:.14em;color:var(--ink2)}
.sched-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border);overflow:visible}
.sched-link{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:12px 6px;text-decoration:none;background:var(--surface);position:relative;transition:transform .18s,box-shadow .18s;z-index:0}
.sched-link::after{content:'';position:absolute;inset:-1.5px;padding:1.5px;background:linear-gradient(var(--angle,0deg),var(--g1),var(--g2),var(--g3),var(--g2),var(--g1));background-size:300% 300%;-webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);-webkit-mask-composite:xor;mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);mask-composite:exclude;opacity:.25;pointer-events:none;animation:borderSpin 2.5s linear infinite paused}
.sched-link:hover{transform:translateY(-3px) scale(1.08);box-shadow:0 8px 20px rgba(0,0,0,.45);z-index:5;background:var(--surface2)}
.sched-link:hover::after{opacity:1;animation-play-state:running}.sched-link:hover .sched-label{color:var(--g2)}
.sched-emoji{font-size:15px;line-height:1}.sched-label{font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3)}
.stats-body{padding:14px;display:flex;flex-direction:column;gap:10px}
.stat-total{display:flex;justify-content:space-between;align-items:center}
.stat-label{font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink2)}
.stat-num{font-family:'Bebas Neue',sans-serif;font-size:36px;line-height:1;background:var(--grad-text);background-size:300% 300%;animation:shimmer 6s ease infinite;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.stat-div{height:1px;background:var(--border)}
#no-results{display:none;grid-column:1/-1;padding:80px 20px;text-align:center;font-family:'Bebas Neue',sans-serif;font-size:30px;letter-spacing:.06em;background:var(--grad-text);background-size:300% 300%;animation:shimmer 5s ease infinite;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
#toTop{position:fixed;bottom:26px;right:26px;width:46px;height:46px;border:none;border-radius:50%;background:var(--grad);background-size:200% 200%;animation:shimmer 4s ease infinite;color:#fff;font-size:18px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px color-mix(in srgb,var(--g1) 40%,transparent);opacity:0;pointer-events:none;transform:translateY(10px);transition:opacity .3s,transform .3s,box-shadow .2s;z-index:500}
#toTop.show{opacity:1;pointer-events:auto;transform:translateY(0)}#toTop:hover{box-shadow:0 6px 24px color-mix(in srgb,var(--g1) 60%,transparent);transform:translateY(-3px)}
footer{border-top:1px solid var(--border);padding:28px 32px;display:flex;align-items:center;justify-content:space-between;gap:16px;background:var(--surface)}
.footer-brand{font-family:'Bebas Neue',sans-serif;font-size:22px;letter-spacing:.05em;background:var(--grad-text);background-size:300% 300%;animation:shimmer 6s ease infinite;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.footer-note{font-family:'DM Mono',monospace;font-size:10px;color:var(--ink3);letter-spacing:.06em;text-align:right}
@media(max-width:900px){.main{grid-template-columns:1fr}.sidebar{position:static;top:auto}}
@media(max-width:640px){.shell,.controls-inner,footer{padding-left:16px;padding-right:16px}.header-inner{grid-template-columns:1fr}.header-meta{align-items:flex-start;flex-direction:row;flex-wrap:wrap}.feed{grid-template-columns:1fr}.brand-title{font-size:64px}.search-box{width:100%}.controls-inner{flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
.editor-pick{grid-column:1/-1;background:linear-gradient(135deg,color-mix(in srgb,var(--g1) 8%,var(--surface)),var(--surface));border:1px solid color-mix(in srgb,var(--g1) 40%,transparent);border-radius:var(--radius);padding:24px 28px;display:flex;flex-direction:column;gap:14px;animation:fadeUp .4s cubic-bezier(.2,.9,.2,1) both;text-decoration:none;color:inherit;position:relative;transition:transform .2s,box-shadow .2s,border-color .2s}
.editor-pick:hover{transform:translateY(-3px);box-shadow:0 12px 32px rgba(0,0,0,.45);border-color:color-mix(in srgb,var(--g1) 60%,transparent)}
.editor-pick-label{font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:.18em;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.editor-pick-headline{font-family:'Bebas Neue',sans-serif;font-size:clamp(22px,3vw,32px);line-height:1.1;background:var(--grad-text);background-size:300% 300%;animation:shimmer 6s ease infinite;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.editor-pick-meta{display:flex;align-items:center;gap:12px}
.editor-pick-tag{font-family:'DM Mono',monospace;font-size:9px;font-weight:500;text-transform:uppercase;letter-spacing:.08em;padding:3px 7px;border-radius:3px;background:color-mix(in srgb,var(--g1) 10%,transparent);color:var(--g2);border:1px solid color-mix(in srgb,var(--g2) 25%,transparent)}
.editor-pick-source{font-family:'DM Mono',monospace;font-size:10px;color:var(--ink3)}
.editor-pick-arrow{font-size:12px;color:var(--ink3);margin-left:auto}
.item-tip{position:fixed;width:310px;max-width:calc(100vw - 32px);visibility:hidden;opacity:0;transform:translateY(8px) scale(.96);transition:opacity .2s ease,transform .2s ease,visibility 0s linear .2s;background:rgba(12,12,20,.97);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,.15);border-left:3px solid var(--g1);border-radius:14px;padding:16px 18px 14px;z-index:9999;box-shadow:0 24px 64px rgba(0,0,0,.75),0 0 0 1px rgba(140,82,255,.18);pointer-events:none}
.item-tip.visible{visibility:visible;opacity:1;transform:translateY(0) scale(1);transition:opacity .2s ease,transform .2s ease,visibility 0s}
.item-tip p{font-size:13px;color:rgba(240,239,245,.88);line-height:1.65;margin:0 0 10px}
.item-tip .tip-src{font-family:'DM Mono',monospace;font-size:9px;color:var(--g1);text-transform:uppercase;letter-spacing:.12em}
[data-theme="light"] .item-tip{background:rgba(237,234,250,.98);border-color:rgba(0,0,0,.08);border-left-color:var(--g1);box-shadow:0 12px 48px rgba(0,0,0,.2)}
[data-theme="light"] .item-tip p{color:var(--ink2)}
[data-theme="light"] .item-tip .tip-src{color:var(--g1)}
.issue-nav{display:flex;justify-content:space-between;align-items:center;padding:24px 0 0;border-top:1px solid var(--border);grid-column:1/-1;margin-top:8px}
.issue-nav-btn{display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink2);font-family:'DM Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.1em;padding:10px 18px;border:1px solid var(--border);border-radius:8px;transition:all .2s}
.issue-nav-btn:hover{color:var(--ink);border-color:var(--g2);transform:translateY(-2px)}
.issue-nav-placeholder{width:120px}"""

JS = """(()=>{const t=localStorage.getItem('ripple-theme')||'dark';document.documentElement.setAttribute('data-theme',t)})();document.getElementById('themeToggle').addEventListener('click',()=>{const c=document.documentElement.getAttribute('data-theme');const n=c==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',n);localStorage.setItem('ripple-theme',n)});
let angle=0;(function spin(){angle=(angle+1.2)%360;const a=angle+'deg';document.querySelectorAll('.item, .sched-link').forEach(e=>{e.style.setProperty('--angle',a)});requestAnimationFrame(spin)})();
let activeFilter='all';
function applyFilters(){const q=(document.getElementById('search').value||'').toLowerCase().trim();const ep=document.querySelector('#feed .editor-pick');if(ep)ep.style.display=(q||activeFilter!=='all')?'none':'';const all=Array.from(document.querySelectorAll('#feed .card'));let n=0;all.forEach(c=>{const cat=activeFilter==='all'||c.dataset.cat===activeFilter;const qo=!q||c.textContent.toLowerCase().includes(q);const s=cat&&qo;c.style.display=s?'':'none';if(s)n++});document.getElementById('no-results').style.display=n===0?'block':'none';updateStats()}
document.getElementById('search').addEventListener('input',applyFilters);
document.querySelectorAll('.chip').forEach(b=>{b.addEventListener('click',()=>{document.querySelectorAll('.chip').forEach(x=>{x.classList.remove('active');x.setAttribute('aria-selected','false')});b.classList.add('active');b.setAttribute('aria-selected','true');activeFilter=b.dataset.filter;applyFilters()})});
const catMeta={'us-sports':{label:'US Sports',emoji:'🏈'},'soccer':{label:'Soccer',emoji:'⚽'},'motorsport':{label:'Motorsport',emoji:'🏎️'},'general':{label:'Business',emoji:'💼'}};
function updateStats(){const v=Array.from(document.querySelectorAll('#feed .card')).filter(c=>c.style.display!=='none');const t=v.reduce((s,c)=>s+c.querySelectorAll('.item').length,0);document.getElementById('count-total').textContent=t||'—';const bd=document.getElementById('cat-breakdown');bd.innerHTML='';Object.entries(catMeta).forEach(([k,m])=>{const cc=v.filter(c=>c.dataset.cat===k);const cnt=cc.reduce((s,c)=>s+c.querySelectorAll('.item').length,0);if(!cnt)return;const p=t?Math.round(cnt/t*100):0;bd.innerHTML+=`<div><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:11px;color:var(--ink2);">${m.emoji} ${m.label}</span><span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--ink3);">${cnt}</span></div><div style="height:2px;background:var(--border);border-radius:2px;overflow:hidden;"><div style="height:100%;width:${p}%;background:linear-gradient(90deg,var(--g1),var(--g2));border-radius:2px;transition:width .45s ease;"></div></div></div>`})}
updateStats();
const toTop=document.getElementById('toTop');window.addEventListener('scroll',()=>toTop.classList.toggle('show',window.scrollY>300),{passive:true});toTop.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
const _tip=document.createElement('div');_tip.className='item-tip';document.body.appendChild(_tip);let _tt,_tipReady=false;function _posT(e){if(!_tipReady)return;const tw=_tip.offsetWidth||310,th=_tip.offsetHeight||90;let x=e.clientX+20,y=e.clientY-th-16;if(x+tw>window.innerWidth-16)x=e.clientX-tw-20;if(y<8)y=e.clientY+20;_tip.style.left=x+'px';_tip.style.top=y+'px';_tip.classList.add('visible')}document.querySelectorAll('.item[data-summary]').forEach(el=>{el.addEventListener('mouseenter',e=>{_tipReady=false;_tt=setTimeout(()=>{_tip.innerHTML='<p>'+el.dataset.summary+'</p><span class="tip-src">'+(el.dataset.source||'')+'</span>';_tipReady=true;_posT(e)},900)});el.addEventListener('mousemove',_posT);el.addEventListener('mouseleave',()=>{clearTimeout(_tt);_tipReady=false;_tip.classList.remove('visible')})});"""

SCHEDULES_HTML = """          <a href="https://www.nfl.com/schedules" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🏈</span><span class="sched-label">NFL</span></a>
          <a href="https://www.nba.com/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🏀</span><span class="sched-label">NBA</span></a>
          <a href="https://www.wnba.com/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🏀</span><span class="sched-label">WNBA</span></a>
          <a href="https://www.mlb.com/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">⚾</span><span class="sched-label">MLB</span></a>
          <a href="https://www.nhl.com/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🏒</span><span class="sched-label">NHL</span></a>
          <a href="https://www.premierleague.com/fixtures" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">⚽</span><span class="sched-label">PL</span></a>
          <a href="https://www.realmadrid.com/en-US/football/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">⚽</span><span class="sched-label">RMA</span></a>
          <a href="https://www.celticfc.com/fixtures" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🍀</span><span class="sched-label">Celtic</span></a>
          <a href="https://www.mlssoccer.com/schedule/" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">⚽</span><span class="sched-label">MLS</span></a>
          <a href="https://www.nwslsoccer.com/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">⚽</span><span class="sched-label">NWSL</span></a>
          <a href="https://www.formula1.com/en/racing/2026.html" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🏎️</span><span class="sched-label">F1</span></a>
          <a href="https://www.nascar.com/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🏁</span><span class="sched-label">NASCAR</span></a>
          <a href="https://www.legavolleyfemminile.it/calendario" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">🏐</span><span class="sched-label">LVF</span></a>
          <a href="https://www.pgatour.com/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">⛳</span><span class="sched-label">PGA</span></a>
          <a href="https://www.lpga.com/tournaments/schedule" target="_blank" rel="noopener" class="sched-link"><span class="sched-emoji">⛳</span><span class="sched-label">LPGA</span></a>"""

def build_html(data: dict) -> str:
    issue_num   = data["issue_number"]
    date_from   = data["date_from"].upper()
    date_to     = data["date_to"].upper()
    year        = data["year"]
    date_range  = f"{date_from} – {date_to} · {year}"

    ticker_html = render_ticker(data.get("ticker", []))

    parts = []
    if data.get("editor_pick"):
        parts.append(render_editor_pick(data["editor_pick"]))
    parts += [render_card(c) for c in data.get("cards", [])]

    # Prev/next navigation
    prev_num = issue_num - 1
    next_num = issue_num + 1
    prev_html = f'<a href="issue-{prev_num}.html" class="issue-nav-btn">← Issue {prev_num}</a>' if prev_num >= 1 else '<div class="issue-nav-placeholder"></div>'
    next_html = f'<a href="issue-{next_num}.html" class="issue-nav-btn">Issue {next_num} →</a>' if os.path.exists(f"issue-{next_num}.html") else '<div class="issue-nav-placeholder"></div>'
    nav_html = f'      <div class="issue-nav">{prev_html}{next_html}</div>'
    parts.append(nav_html)

    cards_html = "\n\n".join(parts)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Ripple Sports Insights — Issue {issue_num}</title>

<script async src="https://www.googletagmanager.com/gtag/js?id=G-ME70MTR6PB"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-ME70MTR6PB', {{ page_title: 'Ripple Sports Insights', page_location: window.location.href, send_page_view: true }});
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,700;1,300&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
{CSS}
</style>
</head>

<body>

<div class="shell">
  <header>
    <div class="ripple-stage"><div class="rring"></div><div class="rring"></div><div class="rring"></div><div class="rring"></div></div>
    <div class="header-inner">
      <div class="brand">
        <div class="brand-eyebrow">// Weekly Digest — Issue {issue_num}</div>
        <h1 class="brand-title">Ripple Sports</h1>
        <span class="brand-title-sub">Insights</span>
        <div class="brand-sub">{date_range}</div>
      </div>
      <div class="header-meta"><button class="theme-btn" id="themeToggle" aria-label="Toggle theme">◐</button></div>
    </div>
  </header>
</div>

<!-- ═══ TICKER ═══ -->
<div class="ticker-wrap">
  <div class="ticker-track">
{ticker_html}
  </div>
</div>

<!-- ═══ CONTROLS ═══ -->
<div class="controls-bar">
  <div class="controls-inner">
    <div class="search-box"><span class="search-icon">⌕</span><input id="search" type="search" placeholder="Search insights…" aria-label="Search insights" /></div>
    <div class="chips" role="tablist">
      <button class="chip active" data-filter="all" role="tab" aria-selected="true">All</button>
      <button class="chip" data-filter="us-sports" role="tab" aria-selected="false">🏈 US Sports</button>
      <button class="chip" data-filter="soccer" role="tab" aria-selected="false">⚽ Soccer</button>
      <button class="chip" data-filter="motorsport" role="tab" aria-selected="false">🏎️ Motorsport</button>
      <button class="chip" data-filter="general" role="tab" aria-selected="false">💼 Business</button>
    </div>
  </div>
</div>

<!-- ═══ MAIN ═══ -->
<div class="shell">
  <div class="main">
    <div class="feed" id="feed">

{cards_html}

      <div id="no-results">NO MATCHING RESULTS</div>
    </div>

    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sidebar-block">
        <div class="sidebar-head"><div class="sidebar-title">📅 Quick Schedules</div></div>
        <div class="sched-grid">
{SCHEDULES_HTML}
        </div>
      </div>
      <div class="sidebar-block">
        <div class="sidebar-head"><div class="sidebar-title">📊 This Week</div></div>
        <div class="stats-body">
          <div class="stat-total"><div class="stat-label">Stories</div><div class="stat-num" id="count-total">—</div></div>
          <div class="stat-div"></div>
          <div id="cat-breakdown" style="display:flex;flex-direction:column;gap:8px;"></div>
        </div>
      </div>
    </aside>
  </div>
</div>

<button id="toTop" aria-label="Back to top">↑</button>

<footer>
  <div class="footer-brand">Ripple Analytics</div>
  <div class="footer-note">© {year} Ripple Analytics Sports Insights<br>All rights reserved · Weekly digest</div>
</footer>

<script>
{JS}
</script>
</body>
</html>"""


# ── index.html updater ────────────────────────────────────────────────────────

def update_index(data: dict, issue_filename: str):
    index_path = "index.html"
    if not os.path.exists(index_path):
        print("  ⚠ index.html not found — skipping index update")
        return

    with open(index_path, encoding="utf-8") as f:
        html = f.read()

    issue_num  = data["issue_number"]

    # Don't insert a duplicate card if this issue already exists in index.html
    if f'href="issue-{issue_num}.html"' in html:
        # Just update the existing card's story count and tags
        print(f"  ✓ index.html already has Issue {issue_num} — skipping duplicate insert")
        return
    date_from  = data["date_from"].upper()
    date_to    = data["date_to"].upper()
    year       = data["year"]
    leagues    = [c["league"] for c in data.get("cards", [])]
    story_count = sum(len(c.get("stories", [])) for c in data.get("cards", []))
    tags_html  = "\n          ".join(f'<span class="issue-tag">{esc(lg)}</span>' for lg in leagues)

    new_card = f"""    <!-- Issue {issue_num} — current -->
    <a href="{issue_filename}" class="issue-card latest">
      <div class="issue-top">
        <div class="issue-num">Issue {issue_num}</div>
        <div class="issue-date">{date_from} – {date_to} · {year}</div>
      </div>
      <div class="issue-body">
        <div class="issue-tags">
          {tags_html}
        </div>
        <div class="issue-count">{story_count}+ stories</div>
        <span class="issue-arrow">↗</span>
      </div>
    </a>"""

    # Remove "latest" class from previous latest card
    html = html.replace('class="issue-card latest"', 'class="issue-card"')

    # Insert new card at top of grid
    grid_marker = '<div class="grid" id="grid">'
    if grid_marker in html:
        html = html.replace(grid_marker, f'{grid_marker}\n\n{new_card}\n')
    else:
        print("  ⚠ Could not find grid in index.html — skipping card insert")
        return

    # Update issue count
    html = re.sub(
        r'(<div class="stat-num" id="total-issues">)\d+(</div>)',
        lambda m: f'{m.group(1)}{issue_num - 13}{m.group(2)}',  # issues start at 14
        html,
    )

    # Update stories count
    html = re.sub(
        r'(<div class="stat-num" id="total-stories">)[\d+]+(</div>)',
        lambda m: f'{m.group(1)}{story_count}+{m.group(2)}',
        html,
    )

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  ✓ index.html updated")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    issue_num = data["issue_number"]
    out_filename = f"issue-{issue_num}.html"

    if os.path.exists(out_filename):
        print(f"  ⚠ {out_filename} already exists!")
        answer = input("  Overwrite? (y/n): ").strip().lower()
        if answer != "y":
            print("  Aborted.")
            sys.exit(0)

    print(f"Generating Issue {issue_num}...")

    html = build_html(data)

    with open(out_filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ {out_filename} written ({len(html):,} bytes)")

    update_index(data, out_filename)

    total = sum(len(c.get("stories", [])) for c in data.get("cards", []))
    print(f"\nDone! Issue {issue_num} · {total} stories · {len(data.get('cards', []))} sections")
    print(f"Open {out_filename} in your browser to preview, then git push.")

if __name__ == "__main__":
    main()
