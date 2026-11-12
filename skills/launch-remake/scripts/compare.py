import ast, json, math, os, sys

rd, fd, sp = sys.argv[1:4]
WIN = [float(x) for x in sys.argv[sys.argv.index("--window") + 1].split(",")] if "--window" in sys.argv else None
R, F = json.load(open(os.path.join(rd, "ref.json"))), json.load(open(os.path.join(fd, "ref.json")))
RF, FF = json.load(open(os.path.join(rd, "frames.json"))), json.load(open(os.path.join(fd, "frames.json")))
S = json.load(open(sp))
W = 960


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


def window(frames, fs, a, b):
    k0, k1 = math.ceil(a * fs - 1e-6) + 2, math.ceil(b * fs - 1e-6)
    rows = [r for r in frames if k0 <= round(r["t"] * fs) < k1 and "diff" in r]
    want = max(0, k1 - k0)
    v = sorted(math.hypot(r["dx"], r["dy"]) / W * 100 * fs for r in rows if "dx" in r)
    fl = sorted(r["fill"] for r in rows if "fill" in r)
    tx = sorted(r["text"] for r in rows if r.get("text"))
    em = run = 0.0
    for r in rows:
        run = run + 1 / fs if r.get("fill") is not None and r["fill"] < 1 else 0.0
        em = max(em, run)
    return dict(speed=round(v[len(v) // 2], 3) if v else None, still=round(100 * sum(r["area"] < 0.015 for r in rows) / len(rows)) if rows else None, cover=len(rows) / want if want else 1.0,
                change=round(sum(r["diff"] for r in rows) / max(1, len(rows)), 2), fill=fl[len(fl) // 2] if fl else None,
                text=tx[len(tx) // 2] if tx else None, empty=round(em, 2))


print(f"render cuts {F['cuts']}, layout jumps {[j['t'] for j in F.get('jumps', [])]}")
print("shot | render s | reference s | speed render / ref | still % render / ref | change render / ref | fill % render / ref | text % render / ref | empty s render / ref")
FPS = round(F.get("fps") or S["fps"])
DUR = round(S["dur"] * FPS) / FPS
cut = lambda t: (round(t * FPS) + 0.5) / FPS
starts = [0.0] + [cut(s["t0"]) for s in S["shots"][1:]]
names = dict(dur=DUR, **{f"cut{i}": v for i, v in enumerate(starts)}, **{k: cut(v) for k, v in S.get("marks", {}).items()})
tm = lambda v: round(float(calc(v, names)) if isinstance(v, str) else float(v), 4)
fails, still = [], [0.0, 0.0, 0.0]
for i, s in enumerate(S["shots"]):
    a, b = starts[i], tm(s["t1"]) if "t1" in s else starts[i + 1] if i + 1 < len(starts) else DUR
    b = min(b, DUR)
    fr = lambda x: math.ceil(x * FPS - 1e-6)
    if WIN and not (fr(WIN[0]) <= fr(a) and fr(b) <= fr(WIN[1])):
        if fr(a) < fr(WIN[1]) and fr(b) > fr(WIN[0]):
            fails.append(f"shot {i} is only partly inside the window: start and end the window on cuts")
        continue
    o = fr(WIN[0]) / FPS if WIN else 0
    f = window(FF, F["sample_fps"], a - o, b - o)
    if "ref_window" in s:
        ra, rb = s["ref_window"]
    elif s.get("ref") is not None:
        ra, rb = R["shots"][s["ref"]]["t0"], R["shots"][s["ref"]]["t1"]
    else:
        ra = rb = None
        fails.append(f"shot {i} has no ref or ref_window")
    if ra is not None and not 0 <= ra < rb <= R["dur"] + 1e-3:
        fails.append(f"shot {i}: its reference window {ra}-{rb} is outside the reference (0-{R['dur']} s)")
    r = window(RF, R["sample_fps"], ra, rb) if ra is not None else dict(speed=None, still=None, change=None, fill=None, text=None, empty=None)
    for side, m in (("render", f), ("reference", r)):
        if m["still"] is not None and m["cover"] < 0.9:
            fails.append(f"shot {i}: only {m['cover']:.0%} of the shot is measured in the {side}")
    low = " EMPTY" if r["empty"] is not None and f["empty"] > r["empty"] + 0.2 else ""
    low += " STILL" if f["still"] is not None and r["still"] is not None and f["still"] > r["still"] + 25 else ""
    hint = " (hint: less fill)" if f["fill"] is not None and r["fill"] and f["fill"] < 0.6 * r["fill"] else ""
    hint += " (hint: smaller text)" if f["text"] and r.get("text") and f["text"] < 0.7 * r["text"] else ""
    fails += [f"shot {i}{low}"] if low else []
    if ra is not None and (f["still"] is None or r["still"] is None):
        fails.append(f"shot {i} has no measured frames in the {'render' if f['still'] is None else 'reference'}")
    if f["still"] is not None and r["still"] is not None:
        still[0] += f["still"] * (b - a)
        still[1] += r["still"] * (b - a)
        still[2] += b - a
    print(f"{i} | {a:.2f}-{b:.2f} | {ra}-{rb} | {f['speed']} / {r['speed']} | {f['still']} / {r['still']} | {f['change']} / {r['change']} | {f['fill']} / {r['fill']} | {f['text']} / {r.get('text')} | {f['empty']} / {r['empty']}{low}{hint}")
if still[2]:
    fm, rm = still[0] / still[2], still[1] / still[2]
    print(f"stillness over the mapped shots: render {fm:.0f}%, reference windows {rm:.0f}%")
    if fm > rm + 10:
        fails.append(f"the film is {fm - rm:.0f} points stiller than its reference windows")
ra, fa = R.get("audio") or {}, F.get("audio") or {}
if ra and fa:
    for k in ("lufs", "lra", "peak", "sub_pct", "mid_pct", "centroid_hz", "bpm", "beat_strength", "onsets_per_s", "side_db"):
        print(f"audio {k}: render {fa.get(k)} / ref {ra.get(k)}")
if not still[2]:
    fails.append("no shot was compared: check --window and each shot's ref_window")
print("motion match: " + ("FAIL: " + "; ".join(fails) if fails else "pass"))
sys.exit(1 if fails else 0)
