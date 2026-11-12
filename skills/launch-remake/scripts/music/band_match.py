import os, subprocess, sys, tempfile
import numpy as np

ref, ss, src, dst = sys.argv[1:5]
cap = float(sys.argv[5]) if len(sys.argv) > 5 else 15
smooth = float(sys.argv[6]) if len(sys.argv) > 6 else 0.75
SR = 48000


def bands(p, ss="0", tt=None):
    with tempfile.TemporaryDirectory() as d:
        cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", ss] + (["-t", str(tt)] if tt else []) + ["-i", p, "-vn", "-ac", "2", "-ar", str(SR),
               "-filter_complex", "acrossover=split=70 200 2000:order=4th[b0][b1][b2][b3]"]
        for k in range(4):
            cmd += ["-map", f"[b{k}]", "-f", "f32le", os.path.join(d, f"b{k}.raw")]
        subprocess.run(cmd, check=True)
        out = [np.fromfile(os.path.join(d, f"b{k}.raw"), dtype=np.float32).reshape(-1, 2) for k in range(4)]
    n = min(len(b) for b in out)
    return [b[:n] for b in out]


def env(x, hop):
    m = (x.astype(np.float64) ** 2).mean(1)
    w = int(0.5 * SR)
    c = np.concatenate([[0.0], np.cumsum(m)])
    i = np.arange(0, len(m), hop)
    lo, hi = np.clip(i + (w - 1) // 2 - w + 1, 0, len(m)), np.clip(i + (w - 1) // 2 + 1, 0, len(m))
    return 10 * np.log10((c[hi] - c[lo]) / w + 1e-12)


B = bands(src)
n = len(B[0])
R = bands(ref, ss, n / SR)
hop = int(0.1 * SR)
ER, EB = [env(r, hop) for r in R], [env(b, hop) for b in B]
d = [er[:len(eb)] - eb[:len(er)] for er, eb in zip(ER, EB)]
m = min(len(x) for x in d)
d = np.array([x[:m] for x in d])
level = np.array([eb[:m] for eb in EB])
d -= np.median(d[level > level.max() - 40])
k = max(1, int(smooth / 0.1))
g = [np.convolve(np.clip(x, -cap, cap), np.ones(k) / k, "same") for x in d]
t = np.arange(n) / SR
out = sum(b * (10 ** (np.interp(t, np.arange(m) * 0.1, gi) / 20))[:, None] for b, gi in zip(B, g))
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s24le", dst],
               input=out.astype(np.float32).tobytes(), check=True)
for name, gi in zip(("sub", "low", "mid", "high"), g):
    print(name, "gain dB per 1 s:", " ".join(f"{v:.0f}" for v in gi[::10]))
