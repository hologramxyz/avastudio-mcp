import ast, html, json, math, os, random, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec_path, cap, proj = sys.argv[1], sys.argv[2], sys.argv[3]
S = json.load(open(spec_path))
FPS, (W, H) = int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else S["fps"], S["size"]
DUR = round(S["dur"] * FPS) / FPS
WIN = [math.ceil(float(x) * FPS - 1e-6) / FPS for x in sys.argv[sys.argv.index("--window") + 1].split(",")] if "--window" in sys.argv else [0.0, DUR]
if not 0 <= WIN[0] < WIN[1] <= DUR:
    sys.exit(f"--window must lie inside 0-{DUR} s")
LEN = round(WIN[1] - WIN[0], 6)

LOOK = dict(bg="#000", perspective=1050, origin=[50, 46], edge="0 0 0 1px rgba(200,226,253,.16)",
            dof=dict(offsets=[0, 3, 7, 12, 18, 26], blurs=[1.2, 2.4, 4.5, 8, 14, 22], ramp=6),
            fog=dict(far=0.96, far_at=42, near=0.6, near_at=16), vignette=dict(size=[66, 74], inner=52, dark=0.86),
            bloom=dict(blur=18, bright=1.5, opacity=0.16), grain=0.05, expo_s=2.6, dust=dict(d=1.25, grain=1.9))


def merge(a, b):
    for k, v in b.items():
        a[k] = merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a


look = merge(json.loads(json.dumps(LOOK)), S.get("look", {}))
cut = lambda t: (round(t * FPS) + 0.5) / FPS
starts = [0.0] + [cut(s["t0"]) for s in S["shots"][1:]]
names = dict(dur=DUR, **{f"cut{i}": v for i, v in enumerate(starts)}, **{k: cut(v) for k, v in S.get("marks", {}).items()})


def calc(v, names):
    ops = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}

    def ev(n):
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            return n.value
        if isinstance(n, ast.Name) and n.id in names:
            return names[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        raise ValueError(f"time {v!r}: use numbers, dur, cutN, marks, + - * /")

    return ev(ast.parse(v, mode="eval").body)


def tm(v):
    return round(float(calc(v, names)) if isinstance(v, str) else float(v), 4)


PW = W / 100
shots = []
for i, s in enumerate(S["shots"]):
    t1 = tm(s["t1"]) if "t1" in s else starts[i + 1] if i + 1 < len(starts) else DUR
    sh = dict(t0=starts[i], t1=t1, focus=s["focus"], at=s["at"], rot=s.get("rot", [0, 0, 0]), zoom=s.get("zoom", [1, 1]),
              v=[s.get("drift", [0, 0])[0] * PW, s.get("drift", [0, 0])[1] * PW], dof=dict(s.get("dof", dict(angle=180, center=[50, 50], width=50))),
              vignette=s.get("vignette", [50, 50]), expo=s.get("expo", [0, 0]), solo=s.get("solo"), focus_to=s.get("focus_to"), ease=s.get("ease"), move_d=s.get("move_d"),
              subject=s.get("subject"), bleed=s.get("bleed"))
    if "drift0" in s:
        sh.update(v0=[s["drift0"][0] * PW, s["drift0"][1] * PW], tau=s.get("tau", 1.0), rv=s.get("rv", 0))
    if "rack" in sh["dof"]:
        sh["dof"]["rack"] = [tm(x) for x in sh["dof"]["rack"]]
    shots.append(sh)

events, end = [], None
for e in S.get("events", []):
    e = dict(e)
    for k in ("t", "caret_from", "hide"):
        if k in e:
            e[k] = tm(e[k])
    if "clicks" in e:
        e["clicks"] = [tm(x) for x in e["clicks"]]
    if "path" in e:
        e["path"] = [dict(k, t=tm(k["t"])) for k in e["path"]]
    if "keys" in e:
        e["keys"] = [dict(k, t=tm(k["t"])) for k in e["keys"]]
    if e["type"] == "type":
        r, t, times = random.Random(e.get("seed", 7)), e["t"], []
        j = e.get("jitter", 0.4)
        for ch in e["text"]:
            times.append(round(t, 4))
            t += (1 / e.get("cps", 22)) * r.uniform(1 - j, 1 + j) + (e.get("space_pause", 0.05) if ch == " " else 0)
        e.update(times=times, blink=e.get("blink", 0.5), caret_from=e.get("caret_from", e["t"] - 0.6))
    if e["type"] == "end_line":
        end = e
    events.append(e)

meta = json.load(open(os.path.join(cap, "meta.json")))
esc = lambda v: v.replace("&", "&amp;").replace('"', "&quot;")
def attrs(d, cls):
    d = dict(d)
    d["class"] = (cls + " " + d.get("class", "")).strip()
    return " ".join(f'{k}="{esc(v)}"' for k, v in d.items())

page_html = open(os.path.join(cap, "page.html")).read()
if S["page"].get("videos"):
    os.makedirs(os.path.join(proj, "assets", "cap"), exist_ok=True)

    def live(m, n=iter(range(10 ** 4)), done=set()):
        src, out = m.group(1), os.path.splitext(m.group(1))[0] + "-loop.mp4"
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt:stream_tags=alpha_mode", "-of", "csv=p=0",
                             os.path.join(cap, src)], capture_output=True, text=True).stdout.strip().lower()
        if re.search(r"(^|,)(yuva|rgba|argb|bgra|abgr|gbrap|ya)|,1$", pr):
            print(f"page video {src} has an alpha channel, it stays a still")
            return m.group(0)
        if out not in done:
            r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", os.path.join(cap, src), "-t", str(WIN[1] + 0.5), "-an",
                                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", os.path.join(proj, out)], capture_output=True, text=True)
            if r.returncode:
                print(f"page video {src} is not readable, it stays a still: {r.stderr.strip()[:120]}")
                return m.group(0)
            done.add(out)
        fit = re.search(r'\sdata-cap-fit="([^"]*)"', m.group(0))
        a = re.sub(r'\s(src|data-cap-fit)="[^"]*"', "", m.group(0)[4:-1].rstrip("/")).replace("object-fit:fill", fit.group(1) if fit else "object-fit:cover")
        a = re.sub(r'\sclass="([^"]*)"', r' class="clip \1"', a) if ' class="' in a else a + ' class="clip"'
        ms = f' data-media-start="{WIN[0]}"' if WIN[0] else ""
        vid = "" if re.search(r'\sid="', a) else f' id="capv{next(n)}"'
        return f'<video{vid} src="{out}" muted playsinline data-start="0" data-duration="{LEN}"{ms}{a}></video>'

    page_html = re.sub(r'<img\b[^>]*data-cap-video="(assets/cap/[^"]+)"[^>]*>', live, page_html)
page_css = open(os.path.join(cap, "page.css")).read()

GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded",
           "emoji", "math", "fangsong", "inherit", "initial", "unset", "revert"}
declared = {m.strip("'\" ").lower() for m in re.findall(r"@font-face\s*{[^}]*?font-family:\s*([^;}]+)", page_css)}
def unesc(v):
    def one(m):
        if not m.group(1):
            return m.group(2)
        c = int(m.group(1), 16)
        return "\ufffd" if c == 0 or 0xD800 <= c <= 0xDFFF or c > 0x10FFFF else chr(c)
    return re.sub(r"\\([0-9a-fA-F]{1,6})\s?|\\(.)", one, re.sub(r"\\(\r\n|[\n\r\f])", "", re.sub(r"/\*[\s\S]*?\*/", " ", v.replace("\r\n", "\n"))))


def texts(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from texts(v)
    elif isinstance(o, list):
        for v in o:
            yield from texts(v)


def faces(css):
    stack = []
    for t in re.finditer(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|/\*[\s\S]*?\*/|@font-face\s*{[^}]*}|@layer\s*([^{;]*){|{|}", css):
        g = t.group(0)
        if g[:1] in "\"'/":
            continue
        if g.startswith("@font-face"):
            yield t, (tuple(stack), g)
        elif g == "}":
            stack = stack[:-1]
        else:
            stack.append(t.group(1).strip() if g.startswith("@layer") else "")


def split_top(v):
    out, depth, cur = [], 0, ""
    for ch in v:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return out + [cur.strip()] if cur.strip() else out


def known(n):
    return n.lower() in GENERIC or n.strip("'\"").lower() in declared


def fonty(v):
    for n in split_top(v):
        if n.startswith("var(") and n.endswith(")") and fonty(",".join(split_top(n[4:-1])[1:])):
            return True
        if known(n):
            return True
    return False


def clean(v):
    keep = []
    for n in split_top(v):
        if n.startswith("var(") and n.endswith(")"):
            p = split_top(n[4:-1])
            keep.append(f"var({p[0]}, {clean(','.join(p[1:]))})" if len(p) > 1 else n)
        elif known(n):
            keep.append(n)
    return ", ".join(keep) or "sans-serif"


def stack(m):
    return m.group(1) + clean(m.group(2)) if fonty(m.group(2)) else m.group(0)


page_css = re.sub(r"((?:font-family|--[\w-]+)\s*:\s*)((?:[^;}{(]|\([^()]*(?:\([^()]*\)[^()]*)*\))+)", stack, page_css)
named = re.sub(r"\s+", " ", (unesc(re.sub(r"@font-face\s*{[^}]*}", "", page_css)) + unesc(html.unescape(page_html)) + unesc(" ".join(texts([S, meta]))) + " sora variable").lower())
left, out, last = {}, [], 0
for _, k in faces(page_css):
    left[k] = left.get(k, 0) + 1
for t, k in faces(page_css):
    fam = re.search(r"font-family:\s*([^;}]+)", k[1])
    fam = re.sub(r"\s+", " ", unesc(fam.group(1).strip()).strip("'\" ").lower()) if fam else ""
    left[k] -= 1
    out += [page_css[last:t.start()], "" if left[k] or (fam and fam not in named) else k[1]]
    last = t.end()
page_css = "".join(out) + page_css[last:]
P = S["page"]
L = look
page_box = f'<div {attrs(meta["html_attrs"], "cap-html")}><div {attrs(meta["body_attrs"], "cap-body")}>{page_html}</div></div>'
dv_css = ""
DV = S.get("device")
if DV:
    sw, sh = DV.get("screen", [meta["width"], meta["height"]])
    b, r, top, bg = DV.get("bezel", 12), DV.get("radius", 58), DV.get("top", 50), DV.get("bg", "#121212")
    page_box = (f'<x-phone id="phone"><x-screen id="screen"><x-view id="view"><div id="scroll">{page_box}</div></x-view>'
                f'{DV.get("html", "")}<x-status><b>{DV.get("time", "9:41")}</b><i></i></x-status><x-island></x-island></x-screen></x-phone>')
    dv_css = f"""
#page {{ width:{sw + 2 * b}px; box-shadow:none; }}
#phone {{ position:relative; display:block; width:{sw + 2 * b}px; height:{sh + 2 * b}px; padding:{b}px; box-sizing:border-box; border-radius:{r}px; background:{DV.get('frame', '#1b1b1d')}; box-shadow:inset 0 0 0 1.5px {DV.get('edge', '#3c3c40')}, inset 0 0 0 {b - 3}px #050505; }}
#screen {{ position:relative; display:block; width:{sw}px; height:{sh}px; border-radius:{r - b}px; overflow:hidden; background:{bg}; }}
#view {{ position:absolute; left:0; right:0; top:{top}px; bottom:0; display:block; overflow:hidden; }}
#scroll {{ position:absolute; left:0; top:0; width:{sw}px; }}
x-status {{ position:absolute; left:0; right:0; top:0; height:{top}px; display:flex; align-items:center; justify-content:space-between; padding:0 30px 0 38px; box-sizing:border-box; font:600 15px/1 'Sora Variable',sans-serif; color:#fff; background:{bg}; }}
x-status i {{ width:24px; height:11px; border-radius:4px; border:1.5px solid rgba(255,255,255,.5); padding:1.5px; background:linear-gradient(90deg,#fff 0 72%,transparent 72%) content-box; }}
x-island {{ position:absolute; left:50%; top:11px; width:118px; height:34px; margin-left:-59px; border-radius:20px; background:#000; }}"""
end_css = end_html = ""
if end:
    end_css = f"""
#end {{ position:absolute; inset:0; background:{end.get('bg', '#000')}; display:flex; align-items:center; justify-content:center; }}
#line {{ position:relative; font:{end.get('weight', 500)} {end.get('size', 64)}px/1.2 {end['font']}; letter-spacing:{end.get('tracking', '-.02em')}; white-space:nowrap; color:{end.get('color', '#fff')}; }}
#w1 {{ display:inline-block; background-image:linear-gradient(90deg,{end.get('color', '#fff')} 0 var(--a),{end['sheen']} var(--b),{end.get('color', '#fff')} var(--c)); -webkit-background-clip:text; background-clip:text; color:transparent; }}
#w2 {{ display:inline-block; font-weight:{end.get('rest_weight', 400)}; }}
#w2 b {{ font-weight:{end.get('rest_weight', 400)}; color:{end.get('accent_color', end['sheen'])}; }}"""
    e0 = max(end["t"], WIN[0])
    st = e0 - WIN[0]
    st = round(st, 4) if not WIN[0] else round(st * FPS) / FPS if abs(st * FPS - round(st * FPS)) < 1e-6 else st
    end_at = f'data-start="{st}" data-duration="{round(WIN[1] - e0, 4) if not WIN[0] else round(LEN - st, 9)}"' if e0 < WIN[1] else f'data-start="{LEN}" data-duration="{round(1 / FPS, 4)}"'
    end_html = (f'<div id="end" class="clip" {end_at}><div id="line"><span id="w1">{end["word"]}</span>'
                f'<span id="w2">{end.get("rest", "")}<b>{end.get("accent", "")}</b></span></div></div>')

css = f"""{page_css}
#film {{ position:absolute; inset:0; background:{L['bg']}; overflow:hidden; }}
#stage {{ position:absolute; inset:0; perspective:{L['perspective']}px; perspective-origin:{L['origin'][0]}% {L['origin'][1]}%; overflow:hidden; background:{L['bg']}; }}
#pos,#pitch,#yaw,#roll {{ position:absolute; left:0; top:0; width:0; height:0; transform-style:preserve-3d; transform-origin:0 0; }}
#page {{ position:absolute; left:0; top:0; width:{meta['width']}px; transform-origin:0 0; box-shadow:{L['edge']}; }}
#page *, .ov * {{ transition:none!important; animation:none!important; }}
.ov [data-shell]::before, .ov [data-shell]::after {{ content:none!important; }}
#page [data-cap-pos=sticky] {{ position:relative!important; top:auto!important; }}
#page [data-cap-pos=fixed] {{ position:absolute!important; }}
#page.solo *:not([data-solo]):not([data-solo] *) {{ visibility:hidden !important; }}
#page.solo [data-solo], #page.solo [data-solo] * {{ visibility:visible; }}
.ov {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; pointer-events:none; }}
x-cursor {{ position:absolute; left:0; top:0; transform-origin:0 0; pointer-events:none; opacity:0; filter:drop-shadow(0 2px 4px rgba(0,0,0,.35)); }}
x-cursor svg {{ display:block; }}
.dp {{ display:inline-block; font-style:inherit; }}
.tw-ch {{ display:none; }}
.tw-caret {{ display:inline-block; width:2px; height:1.15em; margin-left:1px; background:currentColor; vertical-align:-.2em; }}
.dof,#fog,#vig,#bloom,#expo,#dith {{ position:absolute; inset:0; pointer-events:none; }}
#dith {{ background:url(assets/noise.png); mix-blend-mode:overlay; opacity:{L['grain']}; }}
#expo {{ background:#000; }}
#bloom {{ backdrop-filter:blur({L['bloom']['blur']}px) brightness({L['bloom']['bright']}); -webkit-backdrop-filter:blur({L['bloom']['blur']}px) brightness({L['bloom']['bright']}); opacity:{L['bloom']['opacity']}; mix-blend-mode:screen; }}
{end_css}{dv_css}
{P.get('css', '')}
"""
data = dict(dur=DUR, win=WIN, fps=FPS, size=[W, H], look=L, page=dict(drop=P.get("drop", []), hide=P.get("hide", [])), overlays=S.get("overlays", []), shots=shots, events=events)
layers = "".join(f'<div class="dof" id="dof{i}"></div>' for i in range(len(L["dof"]["blurs"])))
overlays = "".join(f'<div class="ov" id="{o["id"]}">{o.get("html", "")}</div>' for o in S.get("overlays", []))
css += "".join(o.get("css", "") for o in S.get("overlays", []))
runtime = open(os.path.join(HERE, "runtime.js")).read().replace("__DATA__", json.dumps(data))
film = f"""<template>
<style>
{css}
</style>
<div id="film" data-composition-id="film" data-width="{W}" data-height="{H}" data-start="0" data-duration="{LEN}">
  <svg width="0" height="0" style="position:absolute"><defs id="film-defs"></defs></svg>
  <div id="stage"><div id="pos"><div id="pitch"><div id="yaw"><div id="roll"><div id="page">{page_box}</div></div></div></div></div></div>
  {layers}
  <div id="fog"></div><div id="vig"></div><div id="bloom"></div><div id="expo"></div>
  {overlays}
  <div id="dith"></div>
  {end_html}
</div>
<script>
{runtime}
</script>
</template>
"""
os.makedirs(os.path.join(proj, "compositions"), exist_ok=True)
shutil.copytree(os.path.join(cap, "assets"), os.path.join(proj, "assets"), dirs_exist_ok=True)
shutil.copy(os.path.join(HERE, "..", "templates", "noise.png"), os.path.join(proj, "assets", "noise.png"))
for f in sorted(os.listdir(os.path.join(proj, "assets", "cap"))) if os.path.isdir(os.path.join(proj, "assets", "cap")) else []:
    fp = os.path.join(proj, "assets", "cap", f)
    if f.endswith(".svg"):
        if re.search(r"<(animate|animateTransform|animateMotion|set)\b|@keyframes", open(fp, encoding="utf-8", errors="replace").read()):
            print(f"{f} is an animated SVG and runs on its own clock: replace it with a still or hide it")
    elif f.endswith((".gif", ".webp")):
        n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", fp],
                           capture_output=True, text=True).stdout.strip()
        if n.isdigit() and int(n) > 1:
            if f.endswith(".gif") and not subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", fp, "-frames:v", "1", "-c:v", "copy", fp + ".gif"]).returncode:
                os.replace(fp + ".gif", fp)
            else:
                print(f"{f} is animated and runs on its own clock: replace it with a still or hide it")
open(os.path.join(proj, "compositions", "film.html"), "w").write(film)
open(os.path.join(proj, "index.html"), "w").write(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js"></script>
<style>html,body{{margin:0;background:#000}}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{LEN}" data-width="{W}" data-height="{H}">
<div id="film" data-composition-id="film" data-composition-src="compositions/film.html" data-start="0" data-duration="{LEN}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>
</div><script>window.__timelines=window.__timelines||{{}};window.__timelines["main"]=gsap.timeline({{paused:true}});</script></body></html>
""")
name = os.path.basename(os.path.abspath(proj))
for f, body in [("hyperframes.json", {"paths": {"blocks": "compositions", "assets": "assets"}}), ("meta.json", {"id": name, "name": name}),
                ("package.json", {"name": name, "private": True, "type": "module"})]:
    if not os.path.exists(os.path.join(proj, f)):
        json.dump(body, open(os.path.join(proj, f), "w"), indent=2)
cuts = sorted(starts[1:] + [e["t"] for e in events if e["type"] == "end_line"])
json.dump(dict(cuts=[round(c - WIN[0], 6) for c in cuts if WIN[0] < c < WIN[1]], fps=FPS, dur=LEN, frames=round(LEN * FPS), window=WIN, events=[{k: v for k, v in e.items() if k != "times"} for e in events]),
          open(os.path.join(proj, "build.json"), "w"), indent=1)
print(f"built {proj}: {len(shots)} shots, cuts {[round(c, 4) for c in starts[1:]]}, {len(events)} events, film {os.path.getsize(os.path.join(proj, 'compositions', 'film.html')) // 1024} KB")
