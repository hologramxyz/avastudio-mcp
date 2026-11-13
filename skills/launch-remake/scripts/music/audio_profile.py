import json, os, re, subprocess, sys, tempfile
import numpy as np
SR = 22050
p = sys.argv[1]
ss = sys.argv[2] if len(sys.argv) > 2 else "0"
tt = sys.argv[3] if len(sys.argv) > 3 else "600"
BANDS = {"sub": "lowpass=f=70", "low": "highpass=f=70,lowpass=f=200", "mid": "highpass=f=200,lowpass=f=2000", "air": "highpass=f=5000"}
OUT = {"mono": ("anull", "mono"), **{k: (af, "mono") for k, af in BANDS.items()}, "stereo": ("anull", "stereo")}
probe = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-ss", ss, "-t", "0.05", "-i", p, "-vn", "-f", "null", "-"], capture_output=True, text=True).stderr
pick = re.search(r"Stream #0:(\d+)\S* -> #0:0", probe)
src = f"[0:{pick.group(1)}]" if pick else "[0:a]"
tmp = tempfile.mkdtemp(prefix="aprof-")
graph = f"{src}asplit={len(OUT) + 1}" + "".join(f"[i{k}]" for k in OUT) + "[ieb];" + ";".join(
    f"[i{k}]{af},aresample={SR},aformat=sample_fmts=flt:sample_rates={SR}:channel_layouts={ch}[o{k}]" for k, (af, ch) in OUT.items()) + ";[ieb]ebur128=peak=true[oeb]"
cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-ss", ss, "-t", tt, "-i", p, "-filter_complex", graph]
for k in OUT:
    cmd += ["-map", f"[o{k}]", "-f", "f32le", os.path.join(tmp, k)]
eb = subprocess.run(cmd + ["-map", "[oeb]", "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
def pcm(k):
    v = np.fromfile(os.path.join(tmp, k), dtype=np.float32)
    os.remove(os.path.join(tmp, k))
    return v
PCM = {k: pcm(k) for k in OUT}
os.rmdir(tmp)
x = PCM["mono"]
dur = len(x) / SR
tail = eb[eb.rfind("Summary:"):]
lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
lra = float(re.search(r"LRA:\s+(-?[\d.]+) LU", tail).group(1))
peak = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail).group(1))
def db(v): return 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-9)
st = 0.5
rows = {}
for k in BANDS:
    y = PCM[k]
    n = int(SR * st)
    rows[k] = [float(db(y[i:i + n])) for i in range(0, len(y) - n + 1, n)]
n = 2048; h = 512
win = np.hanning(n)
S = np.abs(np.array([np.fft.rfft(x[i:i + n] * win) for i in range(0, len(x) - n, h)]))
f = np.fft.rfftfreq(n, 1 / SR)
cent = (S * f).sum(1) / (S.sum(1) + 1e-9)
energy = S.sum(1)
loud = energy > np.percentile(energy, 30)
flux = np.maximum(0, np.diff(S, axis=0)).sum(1)
flux = flux - np.convolve(flux, np.ones(43) / 43)[21:21 + len(flux)]
flux[flux < 0] = 0
ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
fps = SR / h
lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
lag = lo + int(np.argmax(ac[lo:hi])) if len(ac) > lo else None
strength = float(ac[lag] / (ac[0] + 1e-9)) if lag else None
thr = flux.mean() + 3 * flux.std()
on = [round((i + 1) * h / SR, 2) for i in range(1, len(flux) - 1) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] > flux[i + 1]]
merged = []
for t in on:
    if not merged or t - merged[-1] > 0.2: merged.append(t)
spec = (S ** 2).mean(0)
tot = spec.sum()
def share(a, b): return round(float(spec[(f >= a) & (f < b)].sum() / tot * 100), 1)
st2 = PCM["stereo"].reshape(-1, 2)
mid, side = (st2[:, 0] + st2[:, 1]) / 2, (st2[:, 0] - st2[:, 1]) / 2
d = dict(file=p.split("/")[-1], dur=round(dur, 2), lufs=lufs, lra=lra, peak=peak,
         sub_pct=share(0, 70), low_pct=share(70, 200), mid_pct=share(200, 2000), hi_pct=share(2000, 11000),
         centroid_hz=round(float(np.median(cent[loud] if loud.any() else cent))), bpm=round(60 * fps / lag, 1) if lag else None, beat_strength=round(strength, 2) if lag else None,
         side_db=round(float(db(side) - db(mid)), 1), onsets_per_s=round(len(merged) / dur, 2), onsets=merged[:40])
print(json.dumps(d))
print("t    " + " ".join(f"{i*st:>4.0f}" if i % 4 == 0 else "    " for i in range(len(rows['sub']))))
for k in BANDS: print(f"{k:4} " + " ".join(f"{v:4.0f}" for v in rows[k]))
