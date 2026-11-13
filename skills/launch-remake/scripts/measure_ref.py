import json, os, subprocess, sys
import cv2
import numpy as np

src, out = sys.argv[1], sys.argv[2]
vsrc = src
cap = cv2.VideoCapture(src)
FPS = cap.get(cv2.CAP_PROP_FPS)
if FPS and abs(FPS - max(1, round(FPS / 30)) * 30) > 0.5 and "--grab" not in sys.argv:
    os.makedirs(out, exist_ok=True)
    vsrc = os.path.join(out, "video-30fps.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-an", "-vf", "fps=30", "-c:v", "libx264", "-crf", "12", vsrc], check=True)
    cap.release()
    cap = cv2.VideoCapture(vsrc)
    FPS = cap.get(cv2.CAP_PROP_FPS)
VW, VH = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
step = max(1, round(FPS / 30))
fs = FPS / step
W = 960
H = int(round(VH * W / VW / 2) * 2)
QH = int(round(160 * H / W))

if "--grab" in sys.argv:
    os.makedirs(os.path.join(out, "grab"), exist_ok=True)
    tiles = []
    for t in [float(x) for x in sys.argv[sys.argv.index("--grab") + 1].split(",")]:
        fi = int(round(t * FPS))
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, f = cap.read()
        f = cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA) if ok else np.zeros((H, W, 3), np.uint8)
        label = f"{fi / FPS:.3f}s f{fi}"
        cv2.putText(f, label, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
        cv2.putText(f, label, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.imwrite(os.path.join(out, "grab", f"{fi / FPS:07.3f}.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 88])
        tiles.append(cv2.resize(f, (480, int(480 * H / W))))
    print(f"wrote {len(tiles)} stills and sheet.jpg to {os.path.join(out, 'grab')}")
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(os.path.join(out, "grab", "sheet.jpg"), cv2.vconcat([cv2.hconcat(tiles[r:r + 4]) for r in range(0, len(tiles), 4)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    sys.exit(0)

os.makedirs(os.path.join(out, "shots"), exist_ok=True)
os.makedirs(os.path.join(out, "windows"), exist_ok=True)


def ncc(a, b):
    a, b = a[9:-9, 16:-16], b[9:-9, 16:-16]
    if a.std() < 1 or b.std() < 1:
        return None
    return round(float(cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)[0, 0]), 3)


def text_h(g):
    e = (cv2.Canny(g, 80, 200) > 0).astype(np.uint8) * 255
    m = cv2.morphologyEx(e, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (W // 60, 3)))
    best = 0.0
    for x, y, w, h, a in cv2.connectedComponentsWithStats(m)[2][1:]:
        if 0.012 * H <= h <= 0.3 * H and w >= 1.5 * h and a >= 0.45 * w * h and e[y:y + h, x:x + w].mean() >= 0.08 * 255:
            best = max(best, h / H * 100)
    return round(best, 1)


rows, thumbs, prev, prev_s, prev_h, prev_q, i = [], [], None, None, None, None, 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    if i % step:
        i += 1
        continue
    t = i / FPS
    c = cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA)
    thumbs.append(cv2.imencode(".jpg", cv2.resize(c, (640, int(640 * H / W)), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])[1])
    g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    s = cv2.resize(g, (320, 180), interpolation=cv2.INTER_AREA).astype(np.int16)
    q = cv2.resize(g, (160, QH), interpolation=cv2.INTER_AREA).astype(np.float32)
    hsv = cv2.cvtColor(cv2.resize(c, (160, 90)), cv2.COLOR_BGR2HSV)
    hist = cv2.normalize(cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 8], [0, 180, 0, 256, 0, 256]), None).flatten()
    r = dict(t=round(t, 4), luma=round(float(g.mean()), 2), p99=round(float(np.percentile(g, 99)), 1))
    e = cv2.resize((cv2.Canny(g, 80, 200) > 0).astype(np.float32), (16, 9), interpolation=cv2.INTER_AREA)
    r["fill"] = round(float((e >= max(0.25 * e.max(), 0.01)).mean()) * 100, 1)
    r["text"] = text_h(g)
    if prev is not None:
        d = np.abs(s - prev_s)
        r.update(diff=round(float(d.mean()), 3), area=round(float((d > 24).mean()), 4),
                 hist=round(float(cv2.compareHist(prev_h, hist, cv2.HISTCMP_BHATTACHARYYA)), 4))
        M = None
        p0 = cv2.goodFeaturesToTrack(prev, 400, 0.01, 8)
        if p0 is not None and len(p0) >= 12:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None, winSize=(31, 31), maxLevel=4)
            a, b = p0[st == 1], p1[st == 1]
            if len(a) >= 12:
                M, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=2.0)
                if M is not None and int(inl.sum()) >= 12:
                    cx, cy = W / 2, H / 2
                    mx, my = M @ np.array([cx, cy, 1.0])
                    r.update(dx=float(mx - cx), dy=float(my - cy), scale=float(np.hypot(M[0, 0], M[1, 0])),
                             rot=float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))), inl=int(inl.sum()))
                else:
                    M = None
        if M is not None:
            Mq = M.copy()
            Mq[:, 2] *= 160 / W
            k = ncc(q, cv2.warpAffine(prev_q, Mq, (160, QH), borderMode=cv2.BORDER_REPLICATE))
        else:
            k = ncc(q, prev_q)
        if k is not None:
            r["ncc"] = k
    rows.append(r)
    prev, prev_s, prev_h, prev_q = g, s, hist, q
    i += 1
cap.release()
n = len(rows)
if n < 2:
    sys.exit(f"{src}: no frames (the video is empty or unreadable)")
dur = i / FPS

diff = np.array([r.get("diff", 0) for r in rows])
area = np.array([r.get("area", 0) for r in rows])
hist = np.array([r.get("hist", 0) for r in rows])
trk = np.array(["dx" in r for r in rows])
cuts, jumps = [], []
for k in range(1, n):
    lo, hi = max(1, k - 15), min(n, k + 16)
    calm = float(np.median(np.delete(diff[lo:hi], k - lo)))
    side = max(diff[k - 1] if k > 1 else 0, diff[k + 1] if k + 1 < n else 0)
    jump = diff[k] >= 1.5 and diff[k] > 6 * max(calm, 0.05) and diff[k] > 4 * side
    lost = (k + 1 < n and trk[k - 1] and not trk[k] and trk[k + 1] and hist[k] >= 0.23 and diff[k] >= 1.5 and diff[k] > side)
    if (jump or lost or (area[k] > 0.45 and diff[k] > 3 * side)) and (not cuts or rows[k]["t"] - cuts[-1] > 0.2):
        if rows[k].get("inl", 0) >= 30:
            jumps.append(dict(t=rows[k]["t"], dx_pct=round(rows[k]["dx"] / W * 100, 2), dy_pct=round(rows[k]["dy"] / W * 100, 2)))
        else:
            cuts.append(rows[k]["t"])
bounds = [0.0] + cuts + [round(dur, 4)]


def pick(t):
    return min(range(n), key=lambda k: abs(rows[k]["t"] - t))


def frame_at(t):
    c = cv2.VideoCapture(vsrc)
    c.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = c.read()
    c.release()
    return cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA) if ok else np.zeros((H, W, 3), np.uint8)


def palette(img, k=5):
    px = cv2.resize(img, (64, 36)).reshape(-1, 3).astype(np.float32)
    _, lab, cen = cv2.kmeans(px, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(lab.flatten(), minlength=k) / len(lab)
    o = np.argsort(share)[::-1]
    return [dict(hex="#%02x%02x%02x" % tuple(int(v) for v in cen[j][::-1]), pct=round(float(share[j]) * 100)) for j in o]


def focus(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gh, gw = g.shape
    grid = np.array([[cv2.Laplacian(g[y * gh // 4:(y + 1) * gh // 4, x * gw // 6:(x + 1) * gw // 6], cv2.CV_64F).var() for x in range(6)] for y in range(4)])
    m = grid.max() + 1e-9
    y, x = np.unravel_index(np.argmax(grid), grid.shape)
    return dict(grid=np.round(grid / m, 2).tolist(), sharpest_pct=[round((x + 0.5) / 6 * 100), round((y + 0.5) / 4 * 100)],
                ratio=round(float(m / max(np.median(grid), 1.0)), 1))


def zoom(ks):
    v = np.log([rows[k]["scale"] for k in ks]) if ks else np.zeros(1)
    lo, hi = np.percentile(v, [20, 80])
    v = v[(v >= lo) & (v <= hi)]
    return round(float(np.expm1(v.mean() * fs)) * 100, 2) if len(v) else 0.0


def med(v):
    return round(float(np.median(v)), 3) if len(v) else None


shots = []
for j, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
    ks = [k for k in range(n) if a <= rows[k]["t"] < b and k > 0 and rows[k]["t"] - a > 1.5 / fs and "dx" in rows[k]]
    sp = [np.hypot(rows[k]["dx"], rows[k]["dy"]) / W * 100 * fs for k in ks]
    head = [s for k, s in zip(ks, sp) if rows[k]["t"] < a + 0.5]
    tail = [s for k, s in zip(ks, sp) if rows[k]["t"] > b - 0.5]
    dx = med([rows[k]["dx"] for k in ks]) or 0
    dy = med([rows[k]["dy"] for k in ks]) or 0
    mid = frame_at((a + b) / 2)
    tiles = [frame_at(min(b - 0.05, a + 0.1)), mid, frame_at(max(a + 0.05, b - 0.1))]
    cv2.imwrite(os.path.join(out, "shots", f"s{j:02d}.jpg"), cv2.hconcat([cv2.resize(x, (640, int(640 * H / W))) for x in tiles]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    sel = [k for k in range(n) if a <= rows[k]["t"] < b and k > 0 and rows[k]["t"] - a > 1.5 / fs]
    shots.append(dict(i=j, t0=round(a, 3), t1=round(b, 3), dur=round(b - a, 3),
                      speed_pct_w_s=dict(median=med(sp), start=med(head), end=med(tail)),
                      dir_deg=round(float(np.degrees(np.arctan2(dy, dx))), 1),
                      vel_pct_w_s=[round(dx / W * 100 * fs, 3), round(dy / W * 100 * fs, 3)],
                      zoom_pct_s=zoom(ks),
                      rot_deg_s=round((med([rows[k]["rot"] for k in ks]) or 0) * fs, 3),
                      tracked_pct=round(len(ks) / max(1, len(sel)) * 100),
                      still_pct=round(float((area[sel] < 0.015).mean()) * 100) if sel else None,
                      luma=round(float(np.mean([rows[k]["luma"] for k in range(n) if a <= rows[k]["t"] < b] or [0])), 1),
                      focus=focus(mid), palette=palette(mid)))

HOLD = 2.5
TAIL = 12.0
REL = 0.25
SPLIT = 0.2
WHIP = 150.0
MIN_MOVE, MIN_HOLD, MIN_TRANS = 0.15, 0.25, 0.1
cam = np.array([np.hypot(np.hypot(r["dx"], r["dy"]) / W * 100, abs(np.log(r["scale"])) * 31) * fs if "dx" in r else np.nan for r in rows])
cam_s = np.array([np.nanmedian(cam[max(0, k - 1):k + 2]) if np.isfinite(cam[max(0, k - 1):k + 2]).any() else 0.0 for k in range(n)])
like = np.array([r.get("ncc", 1.0) for r in rows])
kt = np.array([r["t"] for r in rows])
hard = {int(np.argmin(np.abs(kt - c))): "cut" for c in cuts}
hard.update({int(np.argmin(np.abs(kt - j["t"]))): "jump" for j in jumps})

tr = np.zeros(n, bool)
for k in range(1, n - 1):
    if k in hard:
        continue
    lost = not trk[k] and diff[k] >= 1.0
    swap = (trk[k] and like[k] < 0.65 and min(np.nan_to_num(cam[k - 1]), np.nan_to_num(cam[k + 1])) >= HOLD
            and cam[k] < SPLIT * max(cam[k - 1], cam[k + 1]))
    tr[k] = lost or swap
truns, k = [], 1
while k < n:
    if not tr[k]:
        k += 1
        continue
    a = b = k
    while b + 1 < n and b + 1 not in hard and (tr[b + 1] or (b + 2 < n and tr[b + 2] and b + 2 not in hard)):
        b += 1
    for _ in range(2):
        if a - 1 > 0 and a - 1 not in hard and (np.nan_to_num(cam[a - 1]) >= WHIP or hist[a - 1] >= 0.2):
            a -= 1
        if b + 1 < n and b + 1 not in hard and (np.nan_to_num(cam[b + 1]) >= WHIP or hist[b + 1] >= 0.2):
            b += 1
    truns.append((a, b + 1))
    k = b + 1

segs, pos, enter = [], 0, "start"
for a, b, kind in sorted([(k, k + 1, h) for k, h in hard.items()] + [(a, b, "transition") for a, b in truns]):
    if a < pos:
        continue
    if a > pos:
        segs.append([pos, a, None, enter])
    if kind == "transition" and (b - a) / fs >= MIN_TRANS:
        segs.append([a, b, "transition", "continuous" if a > pos else enter])
        pos, enter = b, "transition"
    else:
        pos, enter = a, kind
if pos < n:
    segs.append([pos, n, None, enter])


def valleys(x, i, j):
    best, bp = SPLIT, None
    for p in range(i + 1, j - 1):
        lp, rp = x[i:p].max(), x[p + 1:j].max()
        if (p - i) / fs >= MIN_MOVE and (j - p) / fs >= MIN_MOVE and x[p] < best * min(lp, rp):
            best, bp = x[p] / min(lp, rp), p
    return [i, j] if bp is None else valleys(x, i, bp)[:-1] + valleys(x, bp, j)


def rle(flags):
    out = []
    for i, f in enumerate(flags):
        if out and out[-1][2] == f:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1, f])
    return out


wins = []
for k0, k1, kind, ent in segs:
    if kind:
        wins.append([k0, k1, kind, ent])
        continue
    x = cam_s[k0:k1].copy()
    if len(x) > 1 and ent != "start":
        x[0] = x[1]
    rr = rle([bool(v) for v in x >= HOLD])
    for r_ in rr:
        r_[2] = r_[2] and (r_[1] - r_[0]) / fs >= MIN_MOVE
    rr = rle([f for i, j, f in rr for _ in range(i, j)])
    for q, r_ in enumerate(rr):
        r_[2] = r_[2] or ((r_[1] - r_[0]) / fs < MIN_HOLD and 0 < q < len(rr) - 1)
    rr = rle([f for i, j, f in rr for _ in range(i, j)])
    parts = []
    for q, (i, j, f) in enumerate(rr):
        if not f:
            parts.append([i, j, False])
            continue
        at = valleys(x, i, j)
        sub = [[at[z], at[z + 1], True] for z in range(len(at) - 1)]
        if q + 1 < len(rr):
            a_, e = sub[-1][0], sub[-1][1]
            pk = x[a_:e].max()
            while e - 1 > a_ + MIN_MOVE * fs and x[e - 1] < min(TAIL, REL * pk):
                e -= 1
            sub[-1][1] = rr[q + 1][0] = e
        parts += sub
    for q, (i, j, f) in enumerate(parts):
        wins.append([k0 + i, k0 + j, "move" if f else "hold", ent if q == 0 else "continuous"])
for q in range(len(wins) - 1, -1, -1):
    if wins[q][2] == "transition" or (wins[q][1] - wins[q][0]) / fs >= MIN_TRANS:
        continue
    if wins[q][3] != "continuous" and q + 1 < len(wins) and (q == 0 or wins[q + 1][3] == "continuous") and wins[q + 1][2] != "transition":
        wins[q + 1][0], wins[q + 1][3] = wins[q][0], wins[q][3]
        del wins[q]
    elif wins[q][3] == "continuous" and q > 0 and wins[q - 1][2] != "transition":
        wins[q - 1][1] = wins[q][1]
        del wins[q]


def ease(ks):
    v = cam_s[ks]
    if len(v) < 3 or v.max() < HOLD:
        return None
    tp = (kt[ks[int(np.argmax(v))]] - kt[ks[0]]) / max(kt[ks[-1]] - kt[ks[0]], 1e-9)
    shape = "flat" if v.max() <= 1.5 * np.median(v) else "settle" if tp <= 0.25 else "ramp" if tp >= 0.75 else "bell"
    return dict(t_peak=round(float(tp), 2), shape=shape)


centre = np.array([np.hypot(r["dx"], r["dy"]) / W * 100 * fs if "dx" in r else np.nan for r in rows])
centre_s = np.array([np.nanmedian(centre[max(0, k - 1):k + 2]) if np.isfinite(centre[max(0, k - 1):k + 2]).any() else np.nan for k in range(n)])
for name in os.listdir(os.path.join(out, "windows")):
    if name.startswith("w") and name.endswith(".jpg"):
        os.remove(os.path.join(out, "windows", name))
windows = []
for j, (k0, k1, kind, ent) in enumerate(wins):
    a, b = rows[k0]["t"], rows[k1]["t"] if k1 < n else round(dur, 4)
    if kind == "hold" and (b - a) < MIN_HOLD and np.nanmedian(np.r_[cam[k0:k1], 0]) >= HOLD:
        kind = "move"
    if kind == "move" and cam_s[k0:k1].max() < HOLD:
        kind = "hold"
    sel = [k for k in range(k0, k1) if rows[k]["t"] >= a + 2 / fs and "diff" in rows[k]] or [k for k in range(k0, k1) if "diff" in rows[k]]
    ks = [k for k in sel if "dx" in rows[k]]
    sp = [centre[k] for k in ks]
    dx = med([rows[k]["dx"] for k in ks]) or 0
    dy = med([rows[k]["dy"] for k in ks]) or 0
    md = float(sorted(sp)[len(sp) // 2]) if sp else None
    pk = max(np.nanmax(np.r_[centre_s[k0:k1], 0]), md or 0)
    tiles = []
    for k in (k0, (k0 + k1 - 1) // 2, k1 - 1):
        f = cv2.imdecode(thumbs[k], cv2.IMREAD_COLOR)
        cv2.putText(f, f"{rows[k]['t']:.2f}", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(f, f"{rows[k]['t']:.2f}", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        tiles.append(f)
    cv2.imwrite(os.path.join(out, "windows", f"w{j:02d}.jpg"), cv2.hconcat(tiles), [cv2.IMWRITE_JPEG_QUALITY, 85])
    windows.append(dict(i=j, t0=a, t1=b, dur=round(b - a, 3), kind=kind, enter=ent,
                        speed_pct_w_s=dict(median=None if md is None else round(md, 3), peak=round(float(pk), 3)),
                        dir_deg=round(float(np.degrees(np.arctan2(dy, dx))), 1),
                        vel_pct_w_s=[round(dx / W * 100 * fs, 3), round(dy / W * 100 * fs, 3)],
                        zoom_pct_s=zoom(ks) if ks else 0.0,
                        still_pct=round(float((area[sel] < 0.015).mean()) * 100) if sel else None,
                        change=round(float(diff[sel].mean()), 2) if sel else None,
                        fill_pct=med([rows[k]["fill"] for k in range(k0, k1)]),
                        text_pct=med([rows[k]["text"] for k in range(k0, k1) if rows[k]["text"]]),
                        ease=ease(list(range(k0 + (ent in ("cut", "jump", "transition")), k1))) if kind != "hold" else None))


still = area[1:] < 0.015
runs, c = [], 0
for s in still.tolist() + [False]:
    if s:
        c += 1
    else:
        if c:
            runs.append(c)
        c = 0
per_sec = [round(float((area[k:k + int(fs)] < 0.015).mean()) * 100) for k in range(1, n, int(fs)) if len(area[k:k + int(fs)])]

sheet = []
for sec in range(int(dur)):
    f = frame_at(sec + 0.02)
    f = cv2.resize(f, (320, int(320 * H / W)))
    cv2.putText(f, f"{sec}s", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    sheet.append(f)
if sheet:
    while len(sheet) % 6:
        sheet.append(np.zeros_like(sheet[0]))
    cv2.imwrite(os.path.join(out, "sheet.jpg"), cv2.vconcat([cv2.hconcat(sheet[r:r + 6]) for r in range(0, len(sheet), 6)]), [cv2.IMWRITE_JPEG_QUALITY, 80])

has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip()
audio = None
if has_audio:
    p = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "music", "audio_profile.py"), src], capture_output=True, text=True)
    audio = json.loads(p.stdout.splitlines()[0]) if p.returncode == 0 and p.stdout else dict(error=p.stderr[-300:])

ref = dict(src=os.path.abspath(src), size=[VW, VH], fps=round(FPS, 3), sample_fps=round(fs, 3), dur=round(dur, 3), cuts=cuts, jumps=jumps, windows=windows,
           still=dict(pct=round(float(still.mean()) * 100), mean_change=round(float(diff[1:].mean()), 2),
                      longest_hold_s=round(max(runs) / fs, 2) if runs else 0, per_second=per_sec),
           shots=shots, audio=audio)
json.dump(ref, open(os.path.join(out, "ref.json"), "w"), indent=1)
json.dump(rows, open(os.path.join(out, "frames.json"), "w"))
print(f"{os.path.basename(src)}: {dur:.2f} s, {len(cuts)} cuts, still {ref['still']['pct']}%, mean change {ref['still']['mean_change']}")
print("cuts", cuts)
print("layout jumps (flow tracks across them, so not cuts)", [(j["t"], j["dx_pct"], j["dy_pct"]) for j in jumps])
for s in shots:
    v = s["speed_pct_w_s"]
    print(f"shot {s['i']:2d} {s['t0']:6.2f}-{s['t1']:6.2f}  speed {v['start']}/{v['median']}/{v['end']} %W/s  dir {s['dir_deg']}  zoom {s['zoom_pct_s']}%/s  tracked {s['tracked_pct']}%  focus x{s['focus']['sharpest_pct']} r{s['focus']['ratio']}  luma {s['luma']}  {s['palette'][0]['hex']}")
for w in windows:
    v, e = w["speed_pct_w_s"], w["ease"]
    print(f"window {w['i']:2d} {w['t0']:6.2f}-{w['t1']:6.2f} {w['dur']:5.2f}s  {w['kind']:10s} after {w['enter']:10s} speed {v['median']}/{v['peak']} %W/s  "
          f"dir {w['dir_deg']}  zoom {w['zoom_pct_s']}%/s  still {w['still_pct']}%  fill {w['fill_pct']}%  text {w['text_pct']}%" + (f"  ease {e['shape']} (peak at {e['t_peak']})" if e else ""))
if audio:
    print("audio", {k: audio.get(k) for k in ("lufs", "lra", "peak", "sub_pct", "centroid_hz", "bpm", "beat_strength", "onsets_per_s")})
