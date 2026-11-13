import json, subprocess, sys
import numpy as np
SR = 22050
def pcm(p, ss="0", tt="600", af="anull"):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", ss, "-t", tt, "-i", p, "-vn", "-ac", "1", "-ar", str(SR), "-af", af, "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)
N, H = 8192, 2048
def stft(x):
    w = np.hanning(N)
    return np.abs(np.array([np.fft.rfft(x[i:i + N] * w) for i in range(0, max(1, len(x) - N), H)]))
F = np.fft.rfftfreq(N, 1 / SR)
EDGES = 30 * 2 ** (np.arange(0, 25) / 3)
def third(S):
    p = (S ** 2).mean(0)
    v = [p[(F >= a) & (F < b)].sum() for a, b in zip(EDGES[:-1], EDGES[1:])]
    d = 10 * np.log10(np.array(v) + 1e-12)
    return d - d.max()
def env(x, st=0.25):
    n = int(SR * st)
    return np.array([20 * np.log10(np.sqrt(np.mean(x[i:i + n] ** 2)) + 1e-7) for i in range(0, len(x) - n + 1, n)])
def chroma(S):
    p = (S ** 2).mean(0)
    c = np.zeros(12)
    keep = (F > 55) & (F < 2000)
    pc = np.round(12 * np.log2(F[keep] / 440)).astype(int) % 12
    np.add.at(c, pc, p[keep])
    return c / (c.max() + 1e-12)
ref, ss, tt = sys.argv[1], sys.argv[2], sys.argv[3]
r = pcm(ref, ss, tt); Sr = stft(r); tr, er, cr = third(Sr), env(r), chroma(Sr)
NAMES = "A A# B C C# D D# E F F# G G#".split()
print("ref chroma top", [NAMES[i] for i in np.argsort(cr)[::-1][:5]])
for c in sys.argv[4:]:
    x = pcm(c, tt=tt); S = stft(x); t, e, ch = third(S), env(x), chroma(S)
    m = min(len(e), len(er))
    best = max(float(np.corrcoef(np.roll(ch, k), cr)[0, 1]) for k in range(12))
    print(json.dumps(dict(file=c.split("/")[-1], dur=round(len(x) / SR, 2), spec_db=round(float(np.sqrt(np.mean((t - tr) ** 2))), 2),
                          env_r=round(float(np.corrcoef(e[:m], er[:m])[0, 1]), 3), dyn_db=round(float(np.percentile(e, 95) - np.percentile(e, 20)), 1),
                          chroma_any_key=round(best, 3), top=[NAMES[i] for i in np.argsort(ch)[::-1][:3]])))
