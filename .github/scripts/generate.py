#!/usr/bin/env python3
"""
Generates self-hosted, animated SVG cards for a GitHub profile README.
No third-party widgets and no watermarks: every SVG is written by this script.

Run from the repo root:   python .github/scripts/generate.py
Optional env vars:        GH_USER, GITHUB_TOKEN, OUT_DIR, STATIC_PREVIEW=1
"""
import base64
import datetime as dt
import html
import json
import os
import re
import urllib.request
from collections import Counter

# ------------------------------------------------------------------ config
USER = os.environ.get("GH_USER", "Adbhut1234")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.environ.get("OUT_DIR", "assets")
STATIC = os.environ.get("STATIC_PREVIEW") == "1"

DISPLAY = "Enc0deX"
EMAIL = "adbhutpandey93@gmail.com"
TAGLINES = [
    "Building modern software with TypeScript",
    "Crafting scalable backends with Python",
    "Hackathon builder & open-source tinkerer",
]
PINNED = [  # (repo, fallback description if the repo has none)
    ("SIH-2026", "Smart India Hackathon build, architecture & scale"),
    ("Codeverse", "Interactive coding platform & dev environment"),
    ("Hackathon-Hack2skill", "Hackathon challenge solution, rapid prototyping"),
    ("Zenith", "Python utility suite & core data pipeline"),
]
STACK = [
    ("TypeScript", "#3178c6"), ("JavaScript", "#f1e05a"), ("Python", "#3572A5"),
    ("React", "#61dafb"), ("Next.js", "#e2e8f0"), ("Tailwind", "#38bdf8"),
    ("Node.js", "#68a063"), ("HTML", "#e34c26"), ("CSS", "#8b5cf6"),
    ("Git", "#f05133"), ("GitHub", "#a78bfa"), ("Docker", "#2496ed"),
    ("Linux", "#facc15"), ("Bash", "#89e051"),
]
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "HTML": "#e34c26", "CSS": "#8b5cf6", "Shell": "#89e051", "Jupyter Notebook": "#DA5B0B",
}
FALLBACK = {"followers": 1, "repos": 5, "stars": 0, "total": 152}

MONO = 'ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace'
SANS = '"Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif'
G1, G2, LIME, VIOLET = "#22e58a", "#2dd4bf", "#c6f432", "#7c5cff"



# ------------------------------------------------------------------ themes
# Pick a theme with THEME env var or change DEFAULT_THEME. Add your own by
# copying a block and editing the hex values on the right-hand side.
DEFAULT_THEME = "crimson"
THEMES = {
    "green": {},  # original palette, no changes
    "crimson": {  # matches the red avatar: red, warm orange/gold, near-black
        "#22e58a": "#f0262f", "#2dd4bf": "#ff8a4c", "#c6f432": "#ffd166", "#7c5cff": "#c0151f",
        "#04120c": "#12060a", "#060a14": "#0a0608",
        "#14c466": "#c8161d", "#a3b800": "#e8641a", "#4b2bff": "#7a0e1a",
        "#031a10": "#1a0508", "#052e1a": "#2e0a10", "#0b2a1c": "#2a0b11", "#0f2a1f": "#2a1015",
        "#020b07": "#0b0305", "#02070a": "#080305", "#0b1f16": "#200a0e",
        "#6ee7b7": "#ffa3aa", "#a7f3d0": "#ffc9ce", "#d1fae5": "#ffe4e6", "#86efac": "#ff9aa2",
        "#4ade80": "#ff6b75", "#b8ff6a": "#ffb347", "#8dffc4": "#ffb3b8",
        "#0e1c17": "#1c0f12", "#0d5236": "#5c1219", "#12834f": "#a3162a", "#20c46e": "#e0243a", "#5dffa8": "#ff7a85",
        "#0e7a4d": "#9b1021", "#67e8f9": "#ffc56e", "#c084fc": "#ff7a85",
    },
}


def recolor(svg):
    mapping = THEMES.get(os.environ.get("THEME", DEFAULT_THEME), {})
    for old, new in mapping.items():
        svg = svg.replace(old, new).replace(old.upper(), new)
    return svg


# ------------------------------------------------------------------ http
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
    except Exception as exc:  # network or rate-limit problems fall back to defaults
        print(f"warn: {url} -> {exc}")
        return None


def esc(s):
    return html.escape(str(s), quote=True)


def ago(iso):
    try:
        d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        days = (dt.datetime.now(dt.timezone.utc) - d).days
    except Exception:
        return "recently"
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


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
    offset = (first.weekday() + 1) % 7  # Sunday = 0
    weeks = []
    for ds in dates:
        idx = (dt.date.fromisoformat(ds) - first).days + offset
        w, dow = divmod(idx, 7)
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
    d["langs"] = [l for l, _ in counts.most_common(4)] or ["TypeScript", "HTML", "Python", "JavaScript"]

    d["avatar"] = None
    # 1) live avatar from GitHub  2) github.com/<user>.png  3) local assets/avatar.png fallback
    api_url = u.get("avatar_url")
    candidates = []
    if api_url:
        candidates.append(api_url + ("&" if "?" in api_url else "?") + "s=220")
    candidates.append(f"https://github.com/{USER}.png?size=220")
    raw = None
    for url in candidates:
        raw = get(url)
        if raw:
            break
    if not raw:
        for fn in ("avatar.png", "avatar.jpg"):
            path = os.path.join(OUT, fn)
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    raw = fh.read()
                print("using local", path)
                break
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
    for name, desc in PINNED:
        info = get(f"https://api.github.com/repos/{USER}/{name}", True) or {}
        langs = get(f"https://api.github.com/repos/{USER}/{name}/languages", True) or {}
        total = sum(langs.values()) or 1
        segs = [(k, v / total) for k, v in sorted(langs.items(), key=lambda x: -x[1])][:3]
        if not segs:
            segs = fallback_langs.get(name, [("Code", 1.0)])
        pinned.append({
            "name": name,
            "desc": info.get("description") or desc,
            "stars": info.get("stargazers_count", 0),
            "ago": ago(info["pushed_at"]) if info.get("pushed_at") else "recently",
            "segs": segs,
        })
    d["pinned"] = pinned
    d["weeks"], d["total"] = contributions()
    return d


# ------------------------------------------------------------------ svg kit
BASE_CSS = """
.mono{font-family:%MONO%}.sans{font-family:%SANS%}
.fu{%OP%animation:fu .9s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes fu{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.b1{animation:d1 11s ease-in-out infinite alternate}
.b2{animation:d2 13s ease-in-out infinite alternate}
.b3{animation:d3 9s ease-in-out infinite alternate}
@keyframes d1{to{transform:translate(140px,30px)}}
@keyframes d2{to{transform:translate(-160px,-22px)}}
@keyframes d3{to{transform:translate(-60px,-40px)}}
.bl{animation:bl 1s steps(1) infinite}
@keyframes bl{50%{opacity:0}}
.pulse{animation:pu 2.2s ease-in-out infinite}
@keyframes pu{50%{opacity:.3}}
""".replace("%MONO%", MONO).replace("%SANS%", SANS).replace("%OP%", "" if STATIC else "opacity:0;")


def open_svg(w, h, label, css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f"<style>{BASE_CSS}{css}</style>")


def fu(content, delay=0.0):
    return f'<g class="fu" style="animation-delay:{delay:.2f}s">{content}</g>'


def frame(w, h, uid, inner=True):
    s = f"""<defs>
<linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#04120c"/><stop offset="1" stop-color="#060a14"/></linearGradient>
<linearGradient id="bd{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{G1}" stop-opacity=".85"/><stop offset=".55" stop-color="{G1}" stop-opacity=".14"/><stop offset="1" stop-color="{VIOLET}" stop-opacity=".65"/></linearGradient>
<filter id="bl{uid}" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="36"/></filter>
<clipPath id="cl{uid}"><rect width="{w}" height="{h}" rx="24"/></clipPath>
</defs>
<g clip-path="url(#cl{uid})">
<rect width="{w}" height="{h}" fill="url(#bg{uid})"/>
<ellipse class="b1" cx="{w * .18:.0f}" cy="-6" rx="250" ry="80" fill="#14c466" opacity=".55" filter="url(#bl{uid})"/>
<ellipse class="b2" cx="{w * .66:.0f}" cy="{h + 8}" rx="250" ry="62" fill="#a3b800" opacity=".32" filter="url(#bl{uid})"/>
<ellipse class="b3" cx="{w}" cy="{h * .85:.0f}" rx="130" ry="80" fill="#4b2bff" opacity=".35" filter="url(#bl{uid})"/>
</g>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="23.5" fill="none" stroke="url(#bd{uid})" stroke-width="1.5"/>"""
    if inner:
        s += (f'<rect x="22" y="20" width="{w - 44}" height="{h - 40}" rx="18" fill="#000" fill-opacity=".18" '
              f'stroke="{G1}" stroke-opacity=".28"/>')
    return s


def typing(lines, x, y, size, color, uid, slot=4.0, cw=0.6):
    """Typewriter that cycles through lines using SMIL (renders inside <img> on GitHub)."""
    n_l = len(lines)
    period = slot * n_l
    out = []
    for i, text in enumerate(lines):
        n = len(text)
        step = size * cw
        t0, sl = i / n_l, 1 / n_l
        pts = [(0.0, 0.0)]
        for k in range(1, n + 1):
            pts.append((t0 + sl * .35 * (k - 1) / n, k * step))
        for k in range(n - 1, -1, -1):
            pts.append((t0 + sl * .88 + sl * .12 * (n - 1 - k) / n, k * step))
        pts.append((1.0, 0.0))
        kt = ";".join(f"{t:.5f}" for t, _ in pts)
        wv = ";".join(f"{v:.1f}" for _, v in pts)
        xv = ";".join(f"{x + v:.1f}" for _, v in pts)
        vis = [(0.0, 0)] if t0 > 0 else []
        vis.append((t0, 1))
        if t0 + sl < 0.99999:
            vis.append((t0 + sl, 0))
        if vis[-1][0] < 1:
            vis.append((1.0, vis[-1][1]))
        vk = ";".join(f"{t:.5f}" for t, _ in vis)
        vv = ";".join(str(v) for _, v in vis)
        out.append(
            f'<clipPath id="{uid}c{i}"><rect x="{x}" y="{y - size}" height="{size * 1.7:.0f}" width="0">'
            f'<animate attributeName="width" dur="{period}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{wv}"/>'
            f"</rect></clipPath>"
            f'<text class="mono" x="{x}" y="{y}" font-size="{size}" fill="{color}" clip-path="url(#{uid}c{i})" '
            f'textLength="{n * size * cw:.1f}" lengthAdjust="spacing">{esc(text)}</text>'
            f'<g class="bl"><rect y="{y - size + 2}" width="2" height="{size * 1.15:.0f}" fill="{G1}" opacity="0">'
            f'<animate attributeName="x" dur="{period}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{xv}"/>'
            f'<animate attributeName="opacity" dur="{period}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{vk}" values="{vv}"/>'
            f"</rect></g>"
        )
    return "".join(out)



def pixel_avatar(data_uri, n=40, colors=14):
    """Vector fallback of the avatar (coloured rects) in case GitHub blocks embedded images."""
    try:
        import io
        from PIL import Image
        raw = base64.b64decode(data_uri.split(",", 1)[1])
        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((n, n), Image.LANCZOS)
        im = im.quantize(colors=colors, method=Image.MEDIANCUT).convert("RGB")
    except Exception as exc:
        print("warn: pixel avatar skipped ->", exc)
        return ""
    cell, px, out = 104 / n, im.load(), []
    for y in range(n):
        x = 0
        while x < n:
            c, x2 = px[x, y], x
            while x2 + 1 < n and px[x2 + 1, y] == c:
                x2 += 1
            out.append(f'<rect x="{-52 + x * cell:.2f}" y="{-52 + y * cell:.2f}" width="{(x2 - x + 1) * cell + .4:.2f}" '
                       f'height="{cell + .4:.2f}" fill="#{c[0]:02x}{c[1]:02x}{c[2]:02x}"/>')
            x = x2 + 1
    return '<g shape-rendering="crispEdges">' + "".join(out) + "</g>"

# ------------------------------------------------------------------ cards
def header(d):
    W, H = 900, 270
    css = """
.rise{opacity:0;animation:rise linear infinite}
@keyframes rise{0%{transform:translateY(0);opacity:0}25%{opacity:.85}100%{transform:translateY(-80px);opacity:0}}
.ring{transform-box:fill-box;transform-origin:center;animation:ring 3s ease-out infinite}
@keyframes ring{0%{transform:scale(1);opacity:.7}100%{transform:scale(1.4);opacity:0}}
"""
    p = [open_svg(W, H, f"{DISPLAY} profile header", css), frame(W, H, "h", inner=False)]
    p.append(f'<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="{G1}" opacity=".14"/></pattern>'
             f'<linearGradient id="nameG" gradientUnits="userSpaceOnUse" x1="250" y1="0" x2="520" y2="0" spreadMethod="reflect">'
             f'<stop offset="0" stop-color="{G1}"/><stop offset=".5" stop-color="#b8ff6a"/><stop offset="1" stop-color="{G2}"/>'
             f'<animateTransform attributeName="gradientTransform" type="translate" values="-270 0;270 0;-270 0" dur="7s" repeatCount="indefinite"/></linearGradient></defs>'
             f'<rect width="{W}" height="{H}" rx="24" fill="url(#dots)"/>')
    parts = [(60, 220, 7, 0.0), (210, 240, 9, 1.5), (330, 250, 8, 3.0), (470, 245, 10, 0.8),
             (590, 255, 7, 2.2), (700, 240, 9, 4.0), (800, 250, 8, 1.1), (420, 262, 11, 5.0)]
    for x, y, dur, delay in parts:
        p.append(f'<circle class="rise" cx="{x}" cy="{y}" r="2.2" fill="{G1}" style="animation-duration:{dur}s;animation-delay:{delay}s"/>')

    # avatar
    av = f'<g transform="translate(140,135)">'
    av += f'<circle class="ring" r="58" fill="none" stroke="{G1}" stroke-width="2"/>'
    av += (f'<circle r="68" fill="none" stroke="{G2}" stroke-opacity=".5" stroke-width="1.5" stroke-dasharray="4 12">'
           f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="20s" repeatCount="indefinite"/></circle>')
    if d["avatar"]:
        av += (f'<clipPath id="av"><circle r="52"/></clipPath><circle r="52" fill="#c8161d"/>'
               f'<g clip-path="url(#av)">{pixel_avatar(d["avatar"])}</g>'
               f'<image xlink:href="{d["avatar"]}" x="-52" y="-52" width="104" height="104" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>')
    else:
        av += f'<circle r="52" fill="#0b1f16"/><text class="sans" y="18" text-anchor="middle" font-size="52" font-weight="800" fill="{G1}">E</text>'
    av += f'<circle r="54" fill="none" stroke="{G1}" stroke-width="3"/></g>'
    p.append(fu(av, 0.1))

    # orbit decoration (right)
    p.append(f'<g transform="translate(800,135)" opacity=".9">'
             f'<circle r="66" fill="none" stroke="{G1}" stroke-opacity=".25" stroke-dasharray="2 8"/>'
             f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="14s" repeatCount="indefinite"/>'
             f'<circle cx="66" r="5" fill="{G1}"/></g>'
             f'<circle r="42" fill="none" stroke="{VIOLET}" stroke-opacity=".45" stroke-dasharray="3 9"/>'
             f'<g><animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="9s" repeatCount="indefinite"/>'
             f'<circle cx="42" r="4" fill="{LIME}"/></g>'
             f'<text class="mono pulse" text-anchor="middle" y="9" font-size="26" font-weight="700" fill="{G1}">&lt;/&gt;</text></g>')

    p.append(fu(f'<text class="mono" x="250" y="78" font-size="14" font-weight="700" letter-spacing="5" fill="{G1}">@{esc(USER.lower())}</text>', 0.25))
    p.append(fu(f'<text class="sans" x="248" y="148" font-size="72" font-weight="800" fill="url(#nameG)">{esc(DISPLAY)}</text>', 0.4))
    p.append(f'<text class="mono" x="250" y="190" font-size="16" fill="{G1}" opacity=".8">&gt;</text>')
    p.append(typing(TAGLINES, 270, 191, 16, "#d1fae5", "ht"))

    x = 250
    for i, lang in enumerate(d["langs"]):
        w = len(lang) * 7.8 + 38
        col = LANG_COLORS.get(lang, G1)
        p.append(fu(f'<g transform="translate({x:.0f},216)"><rect width="{w:.0f}" height="30" rx="15" fill="#031a10" fill-opacity=".7" stroke="{G1}" stroke-opacity=".5"/>'
                    f'<circle cx="16" cy="15" r="4" fill="{col}"/><text class="mono" x="28" y="19.5" font-size="13" font-weight="600" fill="#a7f3d0">{esc(lang)}</text></g>', 1.0 + i * .15))
        x += w + 12
    p.append("</svg>")
    return "".join(p)


def about():
    W, H = 900, 290
    css = ".dot{animation:pu 2.4s ease-in-out infinite}"
    p = [open_svg(W, H, "About me terminal", css), frame(W, H, "a", inner=False)]
    p.append('<rect x="22" y="20" width="856" height="250" rx="16" fill="#02070a" fill-opacity=".7" stroke="#22e58a" stroke-opacity=".25"/>')
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle class="dot" cx="{48 + i * 20}" cy="42" r="5.5" fill="{c}" style="animation-delay:{i * .4}s"/>')
    p.append('<text class="mono" x="450" y="46" text-anchor="middle" font-size="12" fill="#64748b">~/adbhut1234/about.ts</text>')
    p.append('<line x1="22" y1="62" x2="878" y2="62" stroke="#22e58a" stroke-opacity=".15"/>')

    K, I, P, S, N = "#c084fc", "#e2e8f0", "#67e8f9", "#4ade80", "#64748b"
    code = [
        [("const ", K), ("developer ", I), ("= {", N)],
        [("  handle:    ", P), ('"Enc0deX"', S), (",", N)],
        [("  user:      ", P), ('"Adbhut1234"', S), (",", N)],
        [("  focus:     ", P), ('["TypeScript", "Full-Stack", "Python"]', S), (",", N)],
        [("  mindset:   ", P), ('"Clean code, always learning"', S), (",", N)],
        [("  currently: ", P), ('"Building hackathon projects"', S), (",", N)],
        [("};", N)],
    ]
    for i, segs in enumerate(code):
        y = 96 + i * 26
        spans = "".join(f'<tspan fill="{c}">{esc(t).replace(" ", chr(160))}</tspan>' for t, c in segs)
        p.append(fu(f'<text class="mono" x="44" y="{y}" font-size="11" text-anchor="end" fill="#334155">{i + 1}</text>'
                    f'<text class="mono" x="58" y="{y}" font-size="14" xml:space="preserve">{spans}</text>', 0.4 + i * .3))
    p.append(f'<g class="bl"><rect x="80" y="{96 + 6 * 26 - 13}" width="8" height="17" fill="{G1}"/></g>')

    rows = [("CORE FOCUS", "Robust full-stack web applications", G1),
            ("CURRENT QUEST", "Distributed systems & hackathons", LIME),
            ("ASK ME ABOUT", "TypeScript, React, Python, UI design", G2)]
    p.append('<line x1="580" y1="84" x2="580" y2="246" stroke="#22e58a" stroke-opacity=".15"/>')
    for i, (lab, val, col) in enumerate(rows):
        y = 100 + i * 56
        p.append(fu(f'<circle cx="604" cy="{y - 4}" r="4" fill="{col}"><animate attributeName="r" values="3;6;3" dur="2.6s" begin="{i * .5}s" repeatCount="indefinite"/></circle>'
                    f'<text class="mono" x="620" y="{y}" font-size="11" font-weight="700" letter-spacing="3" fill="{col}">{lab}</text>'
                    f'<text class="sans" x="620" y="{y + 22}" font-size="14" fill="#cbd5e1">{esc(val)}</text>', 1.2 + i * .35))
    p.append("</svg>")
    return "".join(p)


def stack():
    W = 900
    chips, x, y, row_h = [], 46, 82, 46
    for i, (name, col) in enumerate(STACK):
        w = len(name) * 8.1 + 44
        if x + w > W - 46:
            x, y = 46, y + row_h
        float_d = 3 + (i % 4) * .6
        chips.append(fu(
            f'<g transform="translate({x:.0f},{y})"><g class="fl" style="animation-duration:{float_d:.1f}s;animation-delay:{(i % 5) * .3:.1f}s">'
            f'<rect width="{w:.0f}" height="34" rx="17" fill="#031a10" fill-opacity=".75" stroke="{col}" stroke-opacity=".55"/>'
            f'<circle cx="18" cy="17" r="5" fill="{col}"/>'
            f'<text class="mono" x="30" y="22" font-size="13" font-weight="600" fill="#e2e8f0">{esc(name)}</text></g></g>', 0.3 + i * .08))
        x += w + 12
    H = y + 34 + 38
    css = ".fl{animation:fl 3.4s ease-in-out infinite alternate}@keyframes fl{from{transform:translateY(-3px)}to{transform:translateY(3px)}}"
    s = [open_svg(W, H, "Tech stack", css), frame(W, H, "s")]
    s.append(f'<text class="mono" x="46" y="56" font-size="12" font-weight="700" letter-spacing="5" fill="{G1}">TOOLBOX &amp; TECHNOLOGIES</text>')
    s.append(f'<circle cx="{W - 60}" cy="52" r="4" fill="{G1}" class="pulse"/>')
    s += chips
    s.append("</svg>")
    return "".join(s)


def donut(cx, cy, segs, uid, r=28, sw=7):
    c = 2 * 3.14159265 * r
    out, css, acc = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#0f2a1f" stroke-width="{sw}"/>'], "", 0.0
    for i, (lang, frac) in enumerate(segs):
        ln = max(c * frac - 2, 1)
        name = f"dn{uid}{i}"
        css += f"@keyframes {name}{{from{{stroke-dasharray:0 {c:.1f}}}to{{stroke-dasharray:{ln:.1f} {c - ln:.1f}}}}}"
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{LANG_COLORS.get(lang, "#8b949e")}" stroke-width="{sw}" '
                   f'transform="rotate({-90 + acc * 360:.1f} {cx} {cy})" stroke-dasharray="{ln:.1f} {c - ln:.1f}" '
                   f'style="animation:{name} 1.4s cubic-bezier(.3,.8,.3,1) {0.9 + i * .2:.1f}s backwards"/>')
        acc += frac
    top = segs[0][1]
    out.append(f'<text class="mono" x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="#d1fae5">{round(top * 100)}%</text>')
    return "".join(out), css


def projects(d):
    W, H = 900, 450
    cards, css = [], ""
    for i, pr in enumerate(d["pinned"]):
        x = 40 + (i % 2) * 420
        y = 92 + (i // 2) * 170
        dn, dcss = donut(x + 340, y + 88, pr["segs"], i)
        css += dcss
        top = pr["segs"][0][0]
        desc = pr["desc"] if len(pr["desc"]) <= 40 else pr["desc"][:39] + "…"
        cw = len(top) * 7 + 30
        body = (
            f'<rect width="400" height="150" rx="14" fill="#020b07" fill-opacity=".75" stroke="{G1}" stroke-opacity=".4"/>'
            f'<line x1="0" y1="32" x2="400" y2="32" stroke="{G1}" stroke-opacity=".25"/>'
            f'<text class="mono" x="16" y="21" font-size="11" fill="#6ee7b7">• {esc(USER)}/{esc(pr["name"])}</text>'
            f'<circle class="pulse" cx="380" cy="16" r="4" fill="{G1}" style="animation-delay:{i * .4}s"/>'
            f'<text class="mono" x="18" y="64" font-size="18" font-weight="700" fill="{G1}">{esc(pr["name"])}<tspan class="bl" fill="{G2}"> _</tspan></text>'
            f'<text class="mono" x="18" y="88" font-size="11.5" fill="#94a3b8">{esc(desc)}</text>'
            f'<g transform="translate(18,100)"><rect width="{cw:.0f}" height="22" rx="11" fill="#052e1a" stroke="{G1}" stroke-opacity=".45"/>'
            f'<circle cx="12" cy="11" r="3.5" fill="{LANG_COLORS.get(top, G1)}"/><text class="mono" x="21" y="15" font-size="11" fill="#86efac">{esc(top)}</text></g>'
            f'<text class="mono" x="18" y="140" font-size="11" fill="#64748b"><tspan fill="#facc15">★</tspan> {pr["stars"]}   updated {esc(pr["ago"])}</text>'
        )
        cards.append(fu(f'<g transform="translate({x},{y})">{body}<g transform="translate(-{x},-{y})">{dn}</g></g>', 0.5 + i * .25))
    s = [open_svg(W, H, "Projects", css), frame(W, H, "p", inner=False)]
    s.append(f'<text class="mono" x="40" y="56" font-size="12" font-weight="700" letter-spacing="4" fill="{G1}">PROJECTS.LIST</text>'
             f'<text class="mono" x="235" y="56" font-size="12" fill="#64748b">$ ./projects.sh --pinned<tspan class="bl" fill="{G1}"> ▌</tspan></text>'
             f'<text class="mono" x="860" y="56" font-size="12" text-anchor="end" fill="#64748b">{len(d["pinned"])} pinned</text>'
             f'<line x1="40" y1="68" x2="860" y2="68" stroke="{G1}" stroke-opacity=".5"><animate attributeName="stroke-opacity" values=".15;.7;.15" dur="4s" repeatCount="indefinite"/></line>')
    s += cards
    s.append("</svg>")
    return "".join(s)


def contrib(d):
    weeks, total = d["weeks"], d["total"]
    cols, step, gy = len(weeks), 14, 98
    W, H = 900, 252
    gx = (W - cols * step + 3) / 2
    colors = ["#0e1c17", "#0d5236", "#12834f", "#20c46e", "#5dffa8"]
    gw = cols * step
    css = ("".join(f".l{i}{{fill:{c}}}" for i, c in enumerate(colors)) +
           f".c{{{'' if STATIC else 'opacity:0;'}transform-box:fill-box;transform-origin:center;animation:pop .6s cubic-bezier(.2,.9,.3,1.4) forwards}}"
           ".t{animation:pop .6s cubic-bezier(.2,.9,.3,1.4) forwards,tw 3.4s ease-in-out infinite}"
           "@keyframes pop{from{opacity:0;transform:scale(.2)}to{opacity:1;transform:scale(1)}}"
           "@keyframes tw{0%,100%{opacity:1}50%{opacity:.5}}"
           f".sweep{{animation:sw 7s linear 2.6s infinite}}@keyframes sw{{from{{transform:translateX(0)}}to{{transform:translateX({gw + 150}px)}}}}")
    s = [open_svg(W, H, f"{total} contributions in the last year", css), frame(W, H, "c")]
    s.append(f'<defs><linearGradient id="swg"><stop offset="0" stop-color="{G1}" stop-opacity="0"/><stop offset=".5" stop-color="#8dffc4" stop-opacity=".55"/><stop offset="1" stop-color="{G1}" stop-opacity="0"/></linearGradient>'
             f'<clipPath id="gc"><rect x="{gx - 4}" y="{gy - 4}" width="{gw + 8}" height="{7 * step + 6}"/></clipPath></defs>')
    s.append(f'<text class="mono" x="46" y="52" font-size="11" font-weight="700" letter-spacing="5" fill="{G1}">CONTRIBUTION TRAIL</text>')
    s.append(f'<text class="sans" x="46" y="80" font-size="22" font-weight="700" fill="#4ade80">{total} contributions in the last year</text>')
    s.append(f'<g transform="translate({W - 46},0)"><circle class="pulse" cx="-44" cy="48" r="4" fill="{G1}"/><text class="mono" x="0" y="52" text-anchor="end" font-size="11" font-weight="700" letter-spacing="3" fill="{G1}">LIVE</text></g>')
    for ci, wk in enumerate(weeks):
        for ri, lv in enumerate(wk):
            if lv is None:
                continue
            cx, cy = gx + ci * step, gy + ri * step
            delay = 0.2 + ci * .035 + ri * .01
            if lv >= 3:
                s.append(f'<rect class="c t l{lv}" x="{cx:.1f}" y="{cy}" width="11" height="11" rx="3" style="animation-delay:{delay:.2f}s,{delay + 1 + (ci % 7) * .4:.2f}s"/>')
            else:
                s.append(f'<rect class="c l{lv}" x="{cx:.1f}" y="{cy}" width="11" height="11" rx="3" style="animation-delay:{delay:.2f}s"/>')
    s.append(f'<g clip-path="url(#gc)"><rect class="sweep" x="{gx - 150}" y="{gy - 4}" width="150" height="{7 * step + 6}" fill="url(#swg)"/></g>')
    ly = gy + 7 * step + 24
    s.append(f'<text class="mono" x="{W - 200}" y="{ly + 9}" font-size="10" text-anchor="end" fill="#64748b">Less</text>')
    for i in range(5):
        s.append(f'<rect class="l{i}" x="{W - 192 + i * 16}" y="{ly}" width="11" height="11" rx="3"/>')
    s.append(f'<text class="mono" x="{W - 106}" y="{ly + 9}" font-size="10" fill="#64748b">More</text></svg>')
    return "".join(s)


def stats(d):
    W, H = 900, 210
    tiles = [("STARS", d["stars"], 10, G1), ("CONTRIBUTIONS", d["total"], 500, VIOLET),
             ("REPOS", d["repos"], 20, LIME), ("FOLLOWERS", d["followers"], 20, G2)]
    css = (".bar{transform-box:fill-box;transform-origin:left center;animation:bar 1.6s cubic-bezier(.2,.8,.2,1) backwards}"
           "@keyframes bar{from{transform:scaleX(0)}}"
           ".draw{stroke-dasharray:600;animation:draw 1.6s ease-out forwards}@keyframes draw{from{stroke-dashoffset:600}to{stroke-dashoffset:0}}")
    s = [open_svg(W, H, "Profile stats", css), frame(W, H, "t", inner=False)]
    s.append(f'<text class="sans" x="40" y="56" font-size="26" font-weight="800" fill="#4ade80">Profile Signal</text>')
    s.append(f'<text class="mono" x="40" y="78" font-size="11" fill="#64748b">live GitHub stats, refreshed daily</text>')
    for i, (lab, val, target, col) in enumerate(tiles):
        x = 40 + i * 210
        frac = max(.06, min(1, val / target))
        s.append(fu(
            f'<g transform="translate({x},96)"><rect class="draw" width="190" height="92" rx="16" fill="#020b07" fill-opacity=".7" stroke="{col}" stroke-opacity=".7" style="animation-delay:{i * .15}s"/>'
            f'<text class="mono" x="20" y="28" font-size="11" font-weight="700" letter-spacing="2" fill="{col}">{lab}</text>'
            f'<text class="sans" x="20" y="64" font-size="34" font-weight="800" fill="{col}">{val}</text>'
            f'<rect x="20" y="76" width="150" height="6" rx="3" fill="#ffffff" fill-opacity=".08"/>'
            f'<rect class="bar" x="20" y="76" width="{150 * frac:.0f}" height="6" rx="3" fill="{col}" style="animation-delay:{.5 + i * .15}s"/></g>', i * .15))
    s.append("</svg>")
    return "".join(s)


def divider():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="6" viewBox="0 0 900 6"><defs>'
            f'<linearGradient id="g" x1="-1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="{G1}" stop-opacity="0"/><stop offset=".5" stop-color="{G1}"/><stop offset="1" stop-color="{G1}" stop-opacity="0"/>'
            f'<animate attributeName="x1" from="-1" to="1" dur="3.5s" repeatCount="indefinite"/><animate attributeName="x2" from="0" to="2" dur="3.5s" repeatCount="indefinite"/></linearGradient></defs>'
            f'<rect y="2" width="900" height="2" rx="1" fill="{G1}" fill-opacity=".12"/><rect y="2" width="900" height="2" rx="1" fill="url(#g)"/></svg>')


def pill(label, value, icon, uid):
    W, H = max(270, int(58 + len(value) * 8.4 + 30)), 62
    css = ".gl{animation:gl 3s ease-in-out infinite}@keyframes gl{50%{stroke-opacity:.25}}"
    return (open_svg(W, H, f"{label} {value}", css) +
            f'<defs><linearGradient id="pb{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{G1}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
            f'<filter id="pf{uid}" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="6"/></filter></defs>'
            f'<rect x="4" y="6" width="{W - 8}" height="{H - 12}" rx="26" fill="{G1}" opacity=".18" filter="url(#pf{uid})" class="pulse"/>'
            f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="29" fill="#04120c"/>'
            f'<rect class="gl" x="2" y="2" width="{W - 4}" height="{H - 4}" rx="29" fill="none" stroke="url(#pb{uid})" stroke-width="2"/>'
            f'<circle cx="32" cy="31" r="15" fill="#0b2a1c" stroke="{G1}" stroke-opacity=".6"/>'
            f'<text class="sans" x="32" y="37" text-anchor="middle" font-size="16" font-weight="800" fill="{G1}">{icon}</text>'
            f'<text class="mono" x="58" y="26" font-size="10" letter-spacing="2" fill="#6ee7b7">{label}</text>'
            f'<text class="mono" x="58" y="44" font-size="13" font-weight="700" fill="#d1fae5">{esc(value)}</text></svg>')


def footer():
    W, H = 900, 150

    def wave(y, amp, color, dur, op, delay):
        path = (f"M0 {y} Q225 {y - amp} 450 {y} T900 {y} T1350 {y} T1800 {y} V{H} H0 Z")
        return (f'<path d="{path}" fill="{color}" fill-opacity="{op}" style="animation:wv {dur}s linear infinite;animation-delay:{delay}s"/>')
    css = "@keyframes wv{from{transform:translateX(0)}to{transform:translateX(-900px)}}"
    return (open_svg(W, H, "Footer", css) +
            f'<defs><linearGradient id="wg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0e7a4d"/><stop offset=".5" stop-color="{G2}"/><stop offset="1" stop-color="#4b2bff"/></linearGradient></defs>' +
            fu(f'<text class="sans" x="450" y="52" text-anchor="middle" font-size="18" font-weight="700" fill="{G1}">Let’s build something great together</text>'
               f'<text class="mono" x="450" y="76" text-anchor="middle" font-size="11" letter-spacing="3" fill="#64748b">OPEN TO COLLABS &amp; HACKATHON TEAMS</text>', 0.2) +
            wave(104, 22, "url(#wg)", 14, .35, 0) + wave(116, 18, "url(#wg)", 10, .5, -3) + wave(130, 14, "url(#wg)", 7, .8, -1) + "</svg>")


# ------------------------------------------------------------------ main
def main():
    d = collect()
    os.makedirs(OUT, exist_ok=True)
    files = {
        "header.svg": header(d), "about.svg": about(), "stack.svg": stack(),
        "projects.svg": projects(d), "contributions.svg": contrib(d), "stats.svg": stats(d),
        "divider.svg": divider(), "footer.svg": footer(),
        "btn-github.svg": pill("GITHUB", f"@{USER}", "G", "g"),
        "btn-email.svg": pill("EMAIL", EMAIL, "@", "e"),
    }
    for name, content in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf8") as f:
            f.write(recolor(content))
        print("wrote", name, f"{len(content) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
