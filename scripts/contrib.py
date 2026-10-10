"""Render the public GitHub contribution calendar as a matrix, in the profile's visual language.

usage: python scripts/contrib.py <github-user> <out.svg>
Stdlib only, so it runs as-is in a GitHub Action.
"""
import re, sys, datetime, urllib.request
from html import unescape

USER, OUT = sys.argv[1], sys.argv[2]
INK, DIM, RULE, MID, PAPER, ACC, SOFT = "#0D0D0B", "#1E1D1A", "#2C2B26", "#8C877B", "#ECE6D9", "#FF5A1F", "#BDB7AA"
MONO = "ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"

req = urllib.request.Request(f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "profile-readme"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

counts = {}
for tid, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
    m = re.match(r"\s*([\d,]+) contribution", unescape(text))
    counts[tid] = int(m.group(1).replace(",", "")) if m else 0

cells = []  # (week, weekday, date, count)
for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
    date = re.search(r'data-date="([\d-]+)"', td)
    cid = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', td)
    if date and cid:
        wd, wk = int(cid.group(1)), int(cid.group(2))
        cells.append((wk, wd, datetime.date.fromisoformat(date.group(1)), counts.get(cid.group(0)[4:-1], 0)))
if not cells:
    sys.exit("no calendar cells found; GitHub markup may have changed")

cells.sort(key=lambda c: c[2])
WEEKS = max(c[0] for c in cells) + 1
total = sum(c[3] for c in cells)
peak = max(c[3] for c in cells)
active = sum(1 for c in cells if c[3])
longest = cur = 0
for c in cells:
    cur = cur + 1 if c[3] else 0
    longest = max(longest, cur)
streak = 0
for c in reversed(cells):
    if c[3] == 0 and c is cells[-1]:
        continue  # today can still be empty without breaking the streak
    if not c[3]:
        break
    streak += 1
today = cells[-1]


def t(x, y, s, size=12, fill=MID, anchor="start", weight=400, ls=0):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" letter-spacing="{ls}">{s}</text>')


W, H, T = 1280, 470, 9
P = min(20, 1060 // WEEKS)
X0, Y0 = 112, 236
gw, gh = WEEKS * P, 7 * P
b, css = [], []
b.append(t(72, 52, "04 / GRADIENT UPDATES", 12, MID, ls=2.5)
         + t(1208, 52, f"REFRESHED DAILY · {today[2]:%d %b %Y}".upper(), 12, MID, "end", ls=2.5)
         + f'<line x1="72" y1="76" x2="1208" y2="76" stroke="{RULE}"/>')
b.append(t(68, 140, "Gradient updates", 46, PAPER, weight=700, ls=-2))
b.append(t(72, 172, "every commit is a step. C ∈ ℕ<tspan baseline-shift=\"super\" font-size=\"9\">7×{}</tspan>, the last 52 weeks".format(WEEKS), 13, MID, ls=.5))
b.append(t(1208, 140, f'‖C‖₁ = <tspan fill="{PAPER}" font-weight="700">{total}</tspan>', 24, ACC, "end"))
b.append(t(1208, 172, "sum of every entry = contributions this year", 11, MID, "end", ls=.5))
# month labels
seen = None
for wk in range(WEEKS):
    first = min((c for c in cells if c[0] == wk), key=lambda c: c[2])
    if first[2].month != seen and first[2].day <= 7:
        seen = first[2].month
        b.append(t(X0 + wk * P, Y0 - 14, f"{first[2]:%b}".lower(), 10.5, MID, ls=1))
for wd, lab in ((1, "mon"), (3, "wed"), (5, "fri")):
    b.append(t(72, Y0 + wd * P + P * .7, lab, 10.5, MID, ls=1))
b.append(f'<path d="M{X0-4} {Y0-4} H{X0-10} V{Y0+gh+4} H{X0-4} M{X0+gw+2} {Y0-4} H{X0+gw+8} V{Y0+gh+4} H{X0+gw+2}" '
         f'fill="none" stroke="{MID}" stroke-width="1.5"/>')
# cells, revealed by a sweep (same gesture as the hero's matmul)
S0, S1 = 4, 46
css.append(f'@keyframes sw{{0%,{S0}%{{transform:translateX(0);opacity:0}}{S0+.5}%{{opacity:1}}'
           f'{S1}%{{transform:translateX({gw-P}px);opacity:1}}{S1+3}%,100%{{transform:translateX({gw-P}px);opacity:0}}}}'
           f'.sw{{animation:sw {T}s linear infinite}}')
lv = lambda n: 0 if n == 0 else min(4, 1 + int(3 * n / max(peak, 1)))
op = {1: .32, 2: .55, 3: .8, 4: 1}
for wk in range(WEEKS):
    tc = S0 + (S1 - S0) * (wk + .5) / WEEKS
    css.append(f'@keyframes w{wk}{{0%,{tc:.1f}%{{opacity:.08}}{tc+.8:.1f}%,94%{{opacity:1}}100%{{opacity:.08}}}}'
               f'.w{wk}{{animation:w{wk} {T}s infinite}}')
for wk, wd, d, n in cells:
    x, y = X0 + wk * P + 2, Y0 + wd * P + 2
    s = P - 4
    if n == 0:
        b.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{DIM}"/>')
    else:
        col = ACC if n == peak else PAPER
        b.append(f'<rect class="w{wk}" x="{x}" y="{y}" width="{s}" height="{s}" fill="{col}" fill-opacity="{op[lv(n)]}">'
                 f'<title>{n} on {d:%d %b %Y}</title></rect>')
b.append(f'<rect class="sw" x="{X0}" y="{Y0-6}" width="{P}" height="{gh+12}" fill="{ACC}" fill-opacity=".08" stroke="{ACC}" stroke-opacity=".7"/>')
tx, ty = X0 + today[0] * P + P / 2, Y0 + today[1] * P + P / 2
b.append(f'<circle cx="{tx}" cy="{ty}" r="{P/2}" fill="none" stroke="{ACC}">'
         f'<animate attributeName="r" values="{P/2-2};{P}" dur="1.6s" repeatCount="indefinite"/>'
         f'<animate attributeName="opacity" values="1;0" dur="1.6s" repeatCount="indefinite"/></circle>')
# footer stats
yb = Y0 + gh + 52
b.append(f'<line x1="72" y1="{yb-26}" x2="1208" y2="{yb-26}" stroke="{RULE}"/>')
stats = [("active days", active), ("max in a day", peak), ("longest streak", longest), ("current streak", streak)]
for i, (k, v) in enumerate(stats):
    b.append(t(72 + i * 200, yb, f'{k}  <tspan fill="{PAPER}">{v}</tspan>', 12, MID, ls=1))
b.append(t(1208, yb, f'less <tspan fill="{DIM}">■</tspan><tspan fill="{PAPER}" fill-opacity=".32">■</tspan>'
                     f'<tspan fill="{PAPER}" fill-opacity=".55">■</tspan><tspan fill="{PAPER}">■</tspan>'
                     f'<tspan fill="{ACC}">■</tspan> peak', 12, MID, "end", ls=1))

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{MONO}">'
       f'<style>text{{font-family:{MONO};white-space:pre}}{"".join(css)}'
       f'@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}</style>'
       f'<rect width="{W}" height="{H}" fill="{INK}"/>{"".join(b)}</svg>')
open(OUT, "w", encoding="utf-8").write(svg)
print(f"{OUT}: {WEEKS} weeks, total {total}, peak {peak}, active {active}, longest {longest}, streak {streak}")
