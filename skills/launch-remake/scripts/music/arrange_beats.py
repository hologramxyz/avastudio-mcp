import json, os, subprocess, sys
import numpy as np

plan_path, dst = sys.argv[1], sys.argv[2]
P = json.load(open(plan_path))
base = os.path.dirname(os.path.abspath(plan_path))
SR, BAR, DUR = 48000, P["bar"], P["duration"]
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(base, P["bed"]), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
bed = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
out = np.zeros((int(DUR * SR) + 1, 2), np.float32)
XF = int(0.006 * SR)
for p0, p1, b0 in P["segments"]:
    i0, i1, j0 = int(round(p0 * SR)), int(round(p1 * SR)), int(round(b0 * SR))
    n = min(i1 - i0 + XF, len(bed) - j0, len(out) - i0)
    seg = bed[j0:j0 + n].copy()
    if p0 > 0:
        seg[:XF] *= np.linspace(0, 1, XF)[:, None]
    if n > i1 - i0:
        seg[i1 - i0:] *= np.linspace(1, 0, n - (i1 - i0))[:, None]
    out[i0:i0 + n] += seg

if P.get("open_filter"):
    pts = P["open_filter"]
    n = int(pts[-1][0] * SR)
    cut = np.exp(np.interp(np.arange(n) / SR, [t for t, _ in pts], np.log([hz for _, hz in pts])))
    a = 1 - np.exp(-2 * np.pi * cut / SR)
    y = out[:n].astype(np.float64)
    for _ in range(4):
        z = np.zeros(2); o = np.empty_like(y)
        for i in range(n):
            z += a[i] * (y[i] - z); o[i] = z
        y = o
    out[:n] = y.astype(np.float32)
fi = int(P.get("fade_in", 0) * SR)
if fi:
    out[:fi] *= np.linspace(0, 1, fi)[:, None] ** 2
for t in P.get("silences", []):
    i0, i1, f = int((t - BAR / 4) * SR), int(t * SR), int(0.012 * SR)
    out[i0 - f:i0] *= np.linspace(1, 0, f)[:, None]
    out[i0:i1] = 0
    out[i1:i1 + f] *= np.linspace(0, 1, f)[:, None]
fo = int(P.get("fade_out", 0) * SR)
if fo:
    out[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "equalizer=f=220:t=q:w=1.2:g=-2", "-c:a", "libmp3lame", "-b:a", "256k", dst], input=out.tobytes(), check=True)
print("ok", dst, DUR)
