#!/usr/bin/env python3
"""
Generates the SVG cards for the GitHub profile README (header, projects,
contributions, stats). Self-hosted: no third-party widgets, no watermarks.

Run from the repo root:   python .github/scripts/generate.py
Optional env vars:        GH_USER, GITHUB_TOKEN, OUT_DIR, STATIC_PREVIEW=1
"""
import base64
import datetime as dt
import html
import io
import json
import os
import re
import urllib.request
from collections import Counter

# ------------------------------------------------------------------ edit these
USER = os.environ.get("GH_USER", "Adbhut1234")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.environ.get("OUT_DIR", "assets")
STATIC = os.environ.get("STATIC_PREVIEW") == "1"

DISPLAY = "Enc0deX"
TAGLINE = "Aspiring AI developer building with TypeScript, JavaScript and Python."
PINNED = ["SIH-2026", "Codeverse", "Hackathon-Hack2skill", "Zenith"]
FEATURED = "Zenith"          # shown first, as a large card
DESCRIPTIONS = {}            # optional, e.g. {"Zenith": "One line about the project"}; GitHub's repo description is used otherwise

# Palette: neutral dark base, one red accent taken from the avatar.
BG, LINE, TXT, MUTED, SOFT = "#0d1117", "#30363d", "#e6edf3", "#8b949e", "#161b22"
ACC = "#e5383b"
HEAT = [SOFT, "#4d1a1f", "#8a2229", "#c4303a", "#ef4a54"]
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "HTML": "#e34c26", "CSS": "#8b5cf6", "Shell": "#89e051", "Jupyter Notebook": "#DA5B0B",
}
FALLBACK = {"followers": 1, "repos": 5, "stars": 0, "total": 152}
SANS = '-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif'


# ------------------------------------------------------------------ helpers
def get(url, as_json=False):
    headers = {"User-Agent": "profile-generator"}
    if as_json:
        headers["Accept"] = "application/vnd.github+json"
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as r:
            data = r.read()
        return json.loads(data) if as_json else data
    except Exception as exc:
        print(f"warn: {url} -> {exc}")
        return None


def esc(s):
    return html.escape(str(s), quote=True)


def ago(iso):
    try:
        days = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    except Exception:
        return ""
    if days < 1:
        return "Updated today"
    if days < 30:
        return f"Updated {days}d ago"
    if days < 365:
        return f"Updated {days // 30}mo ago"
    return f"Updated {days // 365}y ago"


# ------------------------------------------------------------------ data
def contributions():
    raw = get(f"https://github.com/users/{USER}/contributions")
    cells, total = {}, None
    if raw:
        text = raw.decode("utf8", "ignore")
        for tag in re.findall(r"<td[^>]*>", text):
            d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
            lv = re.search(r'data-level="(\d)"', tag)
            if d and lv:
                cells[d.group(1)] = int(lv.group(1))
        m = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", text)
        if m:
            total = int(m.group(1).replace(",", ""))
    if not cells:
        return [[0] * 7 for _ in range(53)], FALLBACK["total"]
    dates = sorted(cells)
    first = dt.date.fromisoformat(dates[0])
    offset = (first.weekday() + 1) % 7
    weeks = []
    for ds in dates:
        w, dow = divmod((dt.date.fromisoformat(ds) - first).days + offset, 7)
        while len(weeks) <= w:
            weeks.append([None] * 7)
        weeks[w][dow] = cells[ds]
    return weeks, (total if total is not None else FALLBACK["total"])


def collect():
    base = f"https://api.github.com/users/{USER}"
    u = get(base, True) or {}
    repos = get(base + "/repos?per_page=100", True) or []
    d = {
        "followers": u.get("followers", FALLBACK["followers"]),
        "repos": u.get("public_repos", FALLBACK["repos"]),
        "stars": sum(r.get("stargazers_count", 0) for r in repos) if repos else FALLBACK["stars"],
    }
    counts = Counter(r["language"] for r in repos if r.get("language"))
    d["langs"] = [l for l, _ in counts.most_common(5)] or ["TypeScript", "JavaScript", "Python", "HTML"]

    # avatar: live API -> github.com/<user>.png -> local assets/avatar.png
    candidates = []
    if u.get("avatar_url"):
        candidates.append(u["avatar_url"] + ("&" if "?" in u["avatar_url"] else "?") + "s=220")
    candidates.append(f"https://github.com/{USER}.png?size=220")
    raw = next((r for r in (get(c) for c in candidates) if r), None)
    if not raw:
        for fn in ("avatar.png", "avatar.jpg"):
            path = os.path.join(OUT, fn)
            if os.path.exists(path):
                raw = open(path, "rb").read()
                print("using local", path)
                break
    d["avatar"] = None
    if raw:
        mime = "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg"
        d["avatar"] = f"data:{mime};base64," + base64.b64encode(raw).decode()

    fallback_langs = {
        "SIH-2026": [("TypeScript", .77), ("CSS", .15), ("JavaScript", .08)],
        "Codeverse": [("TypeScript", .84), ("CSS", .12), ("JavaScript", .04)],
        "Hackathon-Hack2skill": [("JavaScript", .94), ("CSS", .04), ("HTML", .02)],
        "Zenith": [("Python", .53), ("HTML", .40), ("CSS", .07)],
    }
    pinned = []
    for name in PINNED:
        info = get(f"https://api.github.com/repos/{USER}/{name}", True) or {}
        langs = get(f"https://api.github.com/repos/{USER}/{name}/languages", True) or {}
        total = sum(langs.values()) or 1
        segs = [(k, v / total) for k, v in sorted(langs.items(), key=lambda x: -x[1])][:4]
        pinned.append({
            "name": name,
            "desc": info.get("description") or DESCRIPTIONS.get(name, ""),
            "stars": info.get("stargazers_count", 0),
            "ago": ago(info["pushed_at"]) if info.get("pushed_at") else "",
            "segs": segs or fallback_langs.get(name, [("Code", 1.0)]),
        })
    d["pinned"] = pinned
    d["weeks"], d["total"] = contributions()
    return d


# ------------------------------------------------------------------ svg kit
CSS = f"""
text{{font-family:{SANS}}}
.in{{{'' if STATIC else 'opacity:0;'}animation:in .8s cubic-bezier(.2,.7,.2,1) forwards}}
@keyframes in{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.grow{{transform-box:fill-box;transform-origin:left center;animation:grow 1.1s cubic-bezier(.2,.7,.2,1) backwards}}
@keyframes grow{{from{{transform:scaleX(0)}}}}
"""


def open_svg(w, h, label, css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}"><style>{CSS}{css}</style>')


def fin(content, delay=0.0):
    return f'<g class="in" style="animation-delay:{delay:.2f}s">{content}</g>'


def card(w, h):
    return f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}" stroke="{LINE}"/>'


def pixel_avatar(data_uri, size=96, n=40, colors=14):
    """Vector copy of the avatar, used underneath the image in case embedded images are blocked."""
    try:
        from PIL import Image
        raw = base64.b64decode(data_uri.split(",", 1)[1])
        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((n, n), Image.LANCZOS)
        im = im.quantize(colors=colors, method=Image.MEDIANCUT).convert("RGB")
    except Exception as exc:
        print("warn: vector avatar skipped ->", exc)
        return ""
    cell, px, out = size / n, im.load(), []
    for y in range(n):
        x = 0
        while x < n:
            c, x2 = px[x, y], x
            while x2 + 1 < n and px[x2 + 1, y] == c:
                x2 += 1
            out.append(f'<rect x="{-size / 2 + x * cell:.2f}" y="{-size / 2 + y * cell:.2f}" width="{(x2 - x + 1) * cell + .4:.2f}" '
                       f'height="{cell + .4:.2f}" fill="#{c[0]:02x}{c[1]:02x}{c[2]:02x}"/>')
            x = x2 + 1
    return '<g shape-rendering="crispEdges">' + "".join(out) + "</g>"


# ------------------------------------------------------------------ cards
def header(d):
    W, H = 900, 200
    s = [open_svg(W, H, f"{DISPLAY} (@{USER})"), card(W, H)]
    av = f'<g transform="translate(105,100)"><circle r="52" fill="none" stroke="{LINE}" stroke-width="2"/>'
    if d["avatar"]:
        av += (f'<clipPath id="av"><circle r="48"/></clipPath><circle r="48" fill="#c8161d"/>'
               f'<g clip-path="url(#av)">{pixel_avatar(d["avatar"])}</g>'
               f'<image xlink:href="{d["avatar"]}" x="-48" y="-48" width="96" height="96" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>')
    else:
        av += f'<circle r="48" fill="{SOFT}"/><text y="14" text-anchor="middle" font-size="40" font-weight="700" fill="{TXT}">{esc(DISPLAY[:1])}</text>'
    s.append(fin(av + "</g>", 0.1))
    s.append(fin(f'<text x="190" y="62" font-size="14" fill="{MUTED}">@{esc(USER.lower())}</text>', 0.2))
    s.append(fin(f'<text x="188" y="104" font-size="42" font-weight="700" fill="{TXT}">{esc(DISPLAY)}</text>', 0.3))
    s.append(f'<rect class="grow" x="190" y="116" width="44" height="3" rx="1.5" fill="{ACC}" style="animation-delay:.6s"/>')
    s.append(fin(f'<text x="190" y="146" font-size="16" fill="{MUTED}">{esc(TAGLINE)}</text>', 0.5))
    x = 190
    for i, lang in enumerate(d["langs"]):
        w = len(lang) * 7.2 + 34
        s.append(fin(f'<g transform="translate({x:.0f},160)"><rect width="{w:.0f}" height="26" rx="13" fill="{SOFT}" stroke="{LINE}"/>'
                     f'<circle cx="14" cy="13" r="4" fill="{LANG_COLORS.get(lang, MUTED)}"/>'
                     f'<text x="26" y="17.5" font-size="12" fill="{TXT}">{esc(lang)}</text></g>', 0.8 + i * .1))
        x += w + 8
    return "".join(s) + "</svg>"


def lang_bar(uid, x, y, w, h, segs, delay):
    bars, acc = [], 0.0
    for lang, frac in segs:
        sw = w * frac
        bars.append(f'<rect x="{acc:.1f}" width="{max(sw - 1.5, 1):.1f}" height="{h}" fill="{LANG_COLORS.get(lang, MUTED)}"/>')
        acc += sw
    return (f'<clipPath id="bar{uid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}"/></clipPath>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{SOFT}"/>'
            f'<g clip-path="url(#bar{uid})"><g transform="translate({x},{y})"><g class="grow" style="animation-delay:{delay:.2f}s">{"".join(bars)}</g></g></g>')


def projects(d):
    W, H = 900, 370
    items = d["pinned"]
    feat = next((p for p in items if p["name"].lower() == FEATURED.lower()), items[0])
    rest = [p for p in items if p is not feat]
    s = [open_svg(W, H, "Projects"), card(W, H)]
    s.append(f'<text x="40" y="46" font-size="18" font-weight="600" fill="{TXT}">Projects</text>'
             f'<text x="40" y="66" font-size="13" fill="{MUTED}">Main project and other pinned repositories</text>')

    # featured card
    desc = feat["desc"] if len(feat["desc"]) <= 100 else feat["desc"][:99] + "…"
    body = (f'<rect width="820" height="132" rx="10" fill="{SOFT}" stroke="{ACC}" stroke-opacity=".55"/>'
            f'<rect x="0" y="0" width="4" height="132" rx="2" fill="{ACC}"/>'
            f'<text x="24" y="28" font-size="11" font-weight="600" letter-spacing="1.5" fill="{ACC}">MAIN PROJECT</text>'
            f'<text x="24" y="58" font-size="24" font-weight="700" fill="{TXT}">{esc(feat["name"])}</text>')
    if desc:
        body += f'<text x="24" y="80" font-size="13" fill="{MUTED}">{esc(desc)}</text>'
    body += lang_bar("f", 24, 92, 772, 8, feat["segs"], 0.7)
    lx = 24
    for lang, frac in feat["segs"][:3]:
        body += (f'<circle cx="{lx + 4}" cy="118" r="4" fill="{LANG_COLORS.get(lang, MUTED)}"/>'
                 f'<text x="{lx + 14}" y="122" font-size="12" fill="{TXT}">{esc(lang)} <tspan fill="{MUTED}">{round(frac * 100)}%</tspan></text>')
        lx += len(lang) * 7 + 70
    tail = f'★ {feat["stars"]}' + (f'  ·  {feat["ago"]}' if feat["ago"] else "")
    body += f'<text x="796" y="122" font-size="12" text-anchor="end" fill="{MUTED}">{esc(tail)}</text>'
    s.append(fin(f'<g transform="translate(40,88)">{body}</g>', 0.2))

    # other pinned repos
    cw = (820 - 2 * 16) / 3
    for i, pr in enumerate(rest[:3]):
        x, y = 40 + i * (cw + 16), 236
        top = pr["segs"][0]
        desc = pr["desc"] if len(pr["desc"]) <= 30 else pr["desc"][:29] + "…"
        body = (f'<rect width="{cw:.1f}" height="100" rx="8" fill="{BG}" stroke="{LINE}"/>'
                f'<text x="16" y="30" font-size="14" font-weight="600" fill="{ACC}">{esc(pr["name"])}</text>')
        if desc:
            body += f'<text x="16" y="48" font-size="12" fill="{MUTED}">{esc(desc)}</text>'
        body += lang_bar(f"s{i}", 16, 62, cw - 32, 6, pr["segs"], 0.9 + i * .15)
        body += (f'<circle cx="20" cy="86" r="4" fill="{LANG_COLORS.get(top[0], MUTED)}"/>'
                 f'<text x="30" y="90" font-size="12" fill="{TXT}">{esc(top[0])} <tspan fill="{MUTED}">{round(top[1] * 100)}%</tspan></text>'
                 f'<text x="{cw - 16:.1f}" y="90" font-size="12" text-anchor="end" fill="{MUTED}">★ {pr["stars"]}</text>')
        s.append(fin(f'<g transform="translate({x:.1f},{y})">{body}</g>', 0.45 + i * .12))
    return "".join(s) + "</svg>"


def contrib(d):
    """Contribution grid with a snake that crawls column by column and eats the active days."""
    weeks, total = d["weeks"], d["total"]
    W, H = 900, 250
    cols = len(weeks)
    step = (W - 80) / cols
    size = step - 3
    gx, gy = 40, 92
    SEG, TC, PRE, PAUSE = 7, 0.05, 1.8, 2.5          # snake length, seconds per cell, intro, end pause
    T = (cols * 7 - 1) * TC
    D = PRE + T + (SEG - 1) * TC + PAUSE

    def xy(c, r):
        return gx + c * step, gy + r * step

    def kidx(c, r):
        return c * 7 + (r if c % 2 == 0 else 6 - r)

    # corner points of the zig-zag path with the time the head reaches them
    corners = []
    for c in range(cols):
        r0, r1 = (0, 6) if c % 2 == 0 else (6, 0)
        corners.append((kidx(c, r0) * TC, xy(c, r0)))
        corners.append((kidx(c, r1) * TC, xy(c, r1)))

    css = "".join(f".l{i}{{fill:{c}}}" for i, c in enumerate(HEAT))
    css += f".c{{{'' if STATIC else 'opacity:0;'}animation:cf .5s ease-out forwards}}@keyframes cf{{to{{opacity:1}}}}"
    css += f".sn{{animation-duration:{D:.2f}s;animation-iteration-count:infinite;animation-timing-function:linear}}"
    for i in range(SEG):
        off = PRE + i * TC
        x0, y0 = corners[0][1]
        xe, ye = corners[-1][1]
        kf = [f"0%,{(off - 0.001) / D * 100:.3f}%{{transform:translate({x0:.1f}px,{y0:.1f}px);opacity:0}}"
              f"{off / D * 100:.3f}%{{transform:translate({x0:.1f}px,{y0:.1f}px);opacity:1}}"]
        for t, (x, y) in corners[1:]:
            kf.append(f"{(off + t) / D * 100:.3f}%{{transform:translate({x:.1f}px,{y:.1f}px);opacity:1}}")
        end = (off + T) / D * 100
        kf.append(f"{end + .5:.3f}%{{transform:translate({xe:.1f}px,{ye:.1f}px);opacity:0}}100%{{transform:translate({xe:.1f}px,{ye:.1f}px);opacity:0}}")
        css += f"@keyframes sn{i}{{{''.join(kf)}}}"

    s = [None, card(W, H)]
    s.append(f'<text x="40" y="46" font-size="18" font-weight="600" fill="{TXT}">Contributions</text>'
             f'<text x="40" y="66" font-size="13" fill="{MUTED}">{total} in the last year</text>')
    n_eat = 0
    for ci, wk in enumerate(weeks):
        cells = []
        for ri, lv in enumerate(wk):
            if lv is None:
                continue
            x, y = xy(ci, ri)
            cells.append(f'<rect class="l0" x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" rx="2.5"/>')
            if lv > 0:
                pe = (PRE + kidx(ci, ri) * TC) / D * 100
                css += f"@keyframes e{n_eat}{{0%,{pe:.3f}%{{opacity:1}}{pe + .6 / D * 100 + .01:.3f}%,100%{{opacity:0}}}}"
                cells.append(f'<rect class="l{lv}" x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" rx="2.5" '
                             f'style="animation:e{n_eat} {D:.2f}s linear infinite"/>')
                n_eat += 1
        s.append(f'<g class="c" style="animation-delay:{.2 + ci * .018:.2f}s">{"".join(cells)}</g>')
    for i in range(SEG - 1, -1, -1):           # draw tail first so the head sits on top
        shade = ACC if i else "#ff5a5f"
        op = max(.35, 1 - i * .11)
        s.append(f'<rect class="sn" x="0" y="0" width="{size:.1f}" height="{size:.1f}" rx="3.5" fill="{shade}" fill-opacity="{op:.2f}" '
                 f'style="animation-name:sn{i};opacity:0"/>')
    ly = H - 30
    s.append(f'<text x="{W - 190}" y="{ly + 9}" font-size="11" text-anchor="end" fill="{MUTED}">Less</text>')
    for i in range(5):
        s.append(f'<rect class="l{i}" x="{W - 182 + i * 15}" y="{ly}" width="11" height="11" rx="2.5"/>')
    s.append(f'<text x="{W - 100}" y="{ly + 9}" font-size="11" fill="{MUTED}">More</text>')
    s[0] = open_svg(W, H, f"{total} contributions in the last year", css)
    return "".join(s) + "</svg>"


def stats(d):
    W, H = 900, 110
    items = [("Repositories", d["repos"]), ("Stars", d["stars"]), ("Followers", d["followers"]), ("Contributions, last year", d["total"])]
    s = [open_svg(W, H, "Profile numbers"), card(W, H)]
    colw = (W - 80) / len(items)
    for i, (lab, val) in enumerate(items):
        x = 40 + i * colw
        if i:
            s.append(f'<line x1="{x - 20:.0f}" y1="26" x2="{x - 20:.0f}" y2="84" stroke="{LINE}"/>')
        s.append(fin(f'<text x="{x:.0f}" y="46" font-size="12" fill="{MUTED}">{esc(lab)}</text>'
                     f'<text x="{x:.0f}" y="82" font-size="32" font-weight="700" fill="{TXT}">{val}</text>', 0.2 + i * .12))
    return "".join(s) + "</svg>"


def main():
    d = collect()
    os.makedirs(OUT, exist_ok=True)
    files = {"header.svg": header(d), "projects.svg": projects(d),
             "contributions.svg": contrib(d), "stats.svg": stats(d)}
    for name, content in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf8") as f:
            f.write(content)
        print("wrote", name, f"{len(content) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
