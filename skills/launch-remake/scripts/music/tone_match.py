import subprocess, sys
import numpy as np

ref, ss, tt, src, dst = sys.argv[1:6]
cap = float(sys.argv[6]) if len(sys.argv) > 6 else 10
lufs = float(sys.argv[7]) if len(sys.argv) > 7 else -16
SR = 48000


def rd(p, ss="0", tt="600"):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", ss, "-t", tt, "-i", p, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


F0 = 30 * 2 ** (np.arange(0, 25) / 3)
cen = np.sqrt(F0[:-1] * F0[1:])


def thirds(m):
    N = 16384
    w = np.hanning(N)
    S = np.mean([np.abs(np.fft.rfft(m[i:i + N] * w)) ** 2 for i in range(0, len(m) - N, N // 2)], axis=0)
    f = np.fft.rfftfreq(N, 1 / SR)
    return np.array([10 * np.log10(S[(f >= p) & (f < q)].sum() + 1e-15) for p, q in zip(F0[:-1], F0[1:])])


g = thirds(rd(ref, ss, tt)) - thirds(rd(src))
g -= np.median(g)
g = np.convolve(np.clip(g, -cap, cap), [0.25, 0.5, 0.25], "same")
eq = "firequalizer=zero_phase=on:gain_entry='" + ";".join(f"entry({c:.1f},{v:.2f})" for c, v in zip(cen, g)) + "'"
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-af", f"{eq},loudnorm=I={lufs}:TP=-1.5:LRA=11,alimiter=limit=0.88:level=disabled",
                "-ar", str(SR), "-c:a", "pcm_s24le", dst], check=True)
print("gains dB", {int(c): round(float(v), 1) for c, v in zip(cen, g)})
