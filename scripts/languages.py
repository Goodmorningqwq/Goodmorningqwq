"""Count the languages across this account's public repos and draw one SVG.

Runs in a GitHub Action with the token every workflow gets for free, so it
never depends on someone else's API quota. Bytes are summed per language
across every non-fork public repo except this profile repo.
"""
import json, os, urllib.request

USER = os.environ["USER_LOGIN"]
TOKEN = os.environ["GITHUB_TOKEN"]
HIDE = {"HTML", "CSS", "SCSS"}          # markup skews the bar; keep it to real languages
TOP = 6

def get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": USER})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

repos = []
page = 1
while True:
    batch = get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
    repos += batch
    if len(batch) < 100: break
    page += 1

totals = {}
for r in repos:
    if r["fork"] or r["name"].lower() == USER.lower(): continue
    for lang, n in get(r["languages_url"]).items():
        if lang in HIDE: continue
        totals[lang] = totals.get(lang, 0) + n

try:
    colors = get("https://raw.githubusercontent.com/ozh/github-colors/master/colors.json")
    color = lambda l: (colors.get(l) or {}).get("color") or "#8b949e"
except Exception:
    color = lambda l: "#7aa2f7"

ranked = sorted(totals.items(), key=lambda kv: -kv[1])[:TOP]
total = sum(n for _, n in ranked) or 1

# --- draw: tokyonight palette, compact layout -------------------------------
W, PAD = 420, 22
bar_y, bar_h = 58, 8
x = PAD; segs = []
for lang, n in ranked:
    w = (W - 2 * PAD) * n / total
    segs.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{max(w,1):.1f}" height="{bar_h}" fill="{color(lang)}"/>')
    x += w

rows = []
col_w = (W - 2 * PAD) / 2
for i, (lang, n) in enumerate(ranked):
    cx = PAD + (i % 2) * col_w
    cy = bar_y + 34 + (i // 2) * 24
    rows.append(f'<circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{color(lang)}"/>'
                f'<text x="{cx+18}" y="{cy}" class="lang">{lang}</text>'
                f'<text x="{cx+col_w-16}" y="{cy}" class="pct" text-anchor="end">{100*n/total:.1f}%</text>')

H = bar_y + 34 + ((len(ranked) + 1) // 2) * 24 + 4
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Most used languages">
<style>
  .title{{font:600 16px 'Segoe UI',Ubuntu,Sans-Serif;fill:#70a5fd}}
  .lang{{font:400 12px 'Segoe UI',Ubuntu,Sans-Serif;fill:#38bdae}}
  .pct{{font:400 12px 'Segoe UI',Ubuntu,Sans-Serif;fill:#a9b1d6}}
</style>
<rect width="{W}" height="{H}" rx="6" fill="#1a1b27"/>
<text x="{PAD}" y="34" class="title">Most Used Languages</text>
<clipPath id="bar"><rect x="{PAD}" y="{bar_y}" width="{W-2*PAD}" height="{bar_h}" rx="4"/></clipPath>
<g clip-path="url(#bar)">{''.join(segs)}</g>
{''.join(rows)}
</svg>
'''
open("languages.svg", "w", encoding="utf-8").write(svg)
print("repos:", len(repos), "| languages:", ", ".join(f"{l} {100*n/total:.0f}%" for l, n in ranked))
