import subprocess, sys, numpy as np
SR = 22050
def pcm(path, af):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-af", af, "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)
p = sys.argv[1]
B = {"low": "lowpass=f=150", "mid": "highpass=f=150,lowpass=f=2000", "hi": "highpass=f=5000"}
st = 0.5
rows = {}
for k, af in B.items():
    x = pcm(p, af); n = int(SR * st)
    rows[k] = [20 * np.log10(np.sqrt(np.mean(x[i:i + n] ** 2)) + 1e-9) for i in range(0, len(x) - n, n)]
print("t    " + " ".join(f"{i*st:>4.0f}" if i % 4 == 0 else "    " for i in range(len(rows['low']))))
for k in B: print(f"{k:4} " + " ".join(f"{v:4.0f}" for v in rows[k]))
