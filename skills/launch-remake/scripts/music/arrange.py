import json, subprocess, sys
import numpy as np

C = json.load(open(sys.argv[1]))
SR, L = C.get("sr", 48000), C["dur"]
REF = C["ref"]
SUB, LOW, MID = "lowpass=f=70", "highpass=f=70,lowpass=f=200", "highpass=f=200,lowpass=f=2000"


def rd(p, af="anull", ss=0, t=None):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(ss)] + (["-t", str(t)] if t else []) + ["-i", p, "-vn", "-ac", "2", "-ar", str(SR), "-af", af, "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32).reshape(-1, 2).copy()


def flt(x, af):
    cmd = ["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", af, "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, input=x.astype(np.float32).tobytes(), capture_output=True, check=True).stdout, dtype=np.float32).reshape(-1, 2).copy()


def db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.asarray(x) ** 2)) + 1e-9))


def conv(a, w):
    n = len(a) + len(w) - 1
    k = 1 << (n - 1).bit_length()
    full = np.fft.irfft(np.fft.rfft(np.asarray(a, np.float64), k) * np.fft.rfft(w, k), k)[:n]
    s = (min(len(a), len(w)) - 1) // 2
    return full[s:s + max(len(a), len(w))]


def ramp(n, xs, ys):
    return 10 ** (np.interp(np.arange(n) / SR, xs, ys) / 20)[:, None]


def place(buf, x, t, gain=1.0):
    s = int(t * SR)
    if s < 0:
        x, s = x[-s:], 0
    k = min(len(x), len(buf) - s)
    if k > 0:
        buf[s:s + k] += x[:k] * gain


TAIL = C.get("tail", [[0, L], [0, 0]])
rb = C["ref_bed"]
ref_bed = rd(REF, ss=rb[0], t=rb[1])
T = dict(mid=db(flt(ref_bed, MID)), sub=db(flt(ref_bed, SUB)), low=db(flt(ref_bed, LOW)))
print("reference bed levels", {k: round(v, 1) for k, v in T.items()})

P = C["pad"]
HP = f"highpass=f={P['hp']},highpass=f={P['hp']}" if P.get("hp") else "anull"
src = rd(P["file"], HP)
h = int(0.25 * SR)
n = int(P.get("piece_s", L + 0.5) / 0.25)
gap = int(P.get("min_gap_s", 4) / 0.25)
if len(src) <= (n + gap + 1) * h:
    print(f"pad {P['file']} is {len(src) / SR:.1f} s, short for two {P.get('piece_s', L + 0.5)} s pieces {P.get('min_gap_s', 4)} s apart: looping it")
    if len(src) <= 2 * h:
        sys.exit(f"pad {P['file']} is {len(src) / SR:.2f} s, too short to loop")
    one, a = src, np.linspace(0, np.pi / 2, 2 * h)[:, None]
    while len(src) <= (n + gap + 1) * h:
        src = np.concatenate([src[:-2 * h], src[-2 * h:] * np.cos(a) + one[:2 * h] * np.sin(a), one[2 * h:]])
E = np.array([np.mean(src[i:i + h] ** 2) for i in range(0, len(src) - h, h)])
best = min(((10 * np.log10(E[a:a + n] + E[b:b + n] + 1e-12)).std(), a, b) for a in range(len(E) - n) for b in range(a + gap, len(E) - n))
print("pad pieces at", best[1] * 0.25, best[2] * 0.25, "s, swing dB", round(float(best[0]), 2))
pad = (src[best[1] * h:best[1] * h + n * h] + src[best[2] * h:best[2] * h + n * h]) * np.sqrt(0.5)

F0 = 30 * 2 ** (np.arange(0, 25) / 3)


def thirds(x):
    m = x.mean(1)
    N = 16384
    w = np.hanning(N)
    S = np.mean([np.abs(np.fft.rfft(m[i:i + N] * w)) ** 2 for i in range(0, len(m) - N, N // 2)], axis=0)
    f = np.fft.rfftfreq(N, 1 / SR)
    return np.array([10 * np.log10(S[(f >= p) & (f < q)].sum() + 1e-15) for p, q in zip(F0[:-1], F0[1:])])


cen = np.sqrt(F0[:-1] * F0[1:])
use = (cen > 150) & (cen < 11000)
g = thirds(flt(ref_bed, HP)) - thirds(pad)
g -= np.mean(g[use])
g = np.convolve(np.clip(np.where(use, g, 0), -10, 10), [0.25, 0.5, 0.25], "same")
shelf = P.get("shelf")
eq = "firequalizer=zero_phase=on:gain_entry='" + ";".join(f"entry({c:.1f},{v:.2f})" for c, v in zip(cen, g)) + "'"
pad = flt(pad, eq + (f",highshelf=f={shelf[0]}:g={shelf[1]}" if shelf else ""))
print("tone eq dB", [round(float(v), 1) for v in g[use]])

m = pad.mean(1)
w = np.hanning(SR)
w /= w.sum()
env = np.sqrt(conv(m ** 2, w) + 1e-12)
lo, hi = P.get("rider", [-6, 8])
pad = pad * conv(np.clip(np.median(env) / env, 10 ** (lo / 20), 10 ** (hi / 20)), w)[:, None]
pad = pad[:int(L * SR)]
pad *= 10 ** ((T["mid"] - db(flt(pad[2 * SR:int((L - 2.5) * SR)], MID))) / 20)
fi = P.get("fade_in", [1.5, -10])
pad *= ramp(len(pad), [0, fi[0]], [fi[1], 0]) * ramp(len(pad), *TAIL)
bed = pad.copy()

Dr = C.get("drone")
if Dr:
    dr = rd(Dr["file"], f"lowpass=f={Dr.get('lp', 110)},lowpass=f={Dr.get('lp', 110)}", ss=Dr.get("ss", 0), t=L)
    dr *= 10 ** ((T["sub"] - db(flt(dr, SUB))) / 20)
    fi = Dr.get("fade_in", [1.5, -8])
    bed[:len(dr)] += dr[:len(bed)] * ramp(len(bed), [0, fi[0]], [fi[1], 0])[:len(dr)] * ramp(len(bed), *TAIL)[:len(dr)]

Hc = C.get("hit")
if Hc:
    a0, alen = Hc["ref_window"]
    lo_ = rd(REF, "lowpass=f=120", ss=a0, t=alen).mean(1)
    hop, win = int(0.01 * SR), int(0.03 * SR)
    e = np.array([np.sqrt(np.mean(lo_[i:i + win] ** 2)) for i in range(0, len(lo_) - win, hop)])
    floor = np.sqrt(np.mean(e[:50] ** 2))
    e = np.sqrt(np.maximum(e ** 2 - floor ** 2, 0))
    on = int(np.argmax(e > 0.3 * e.max()))
    print("hit onset", round(a0 + on * 0.01, 2), "s, peak dB", round(20 * np.log10(e.max() + 1e-9), 1), "at", round(a0 + int(np.argmax(e)) * 0.01, 2))
    ee = np.interp(np.arange(int(len(e) * hop)) / hop, np.arange(len(e)), e)
    parts = Hc.get("partials", "auto")
    if parts == "auto":
        x = rd(REF, "lowpass=f=120", ss=a0 + on * 0.01, t=1.5).mean(1)
        s = np.abs(np.fft.rfft(x * np.hanning(len(x))))
        f = np.fft.rfftfreq(len(x), 1 / SR)
        k = np.where((f > 20) & (f < 120))[0]
        pk = [i for i in k[1:-1] if s[i] > s[i - 1] and s[i] >= s[i + 1]]
        pk = sorted(pk, key=lambda i: -s[i])[:4]
        parts = [[round(float(f[i]), 1), round(float(s[i] / s[pk[0]]), 2)] for i in pk]
    print("partials", parts)

    def f0(x):
        mm = x.mean(1)
        s = np.abs(np.fft.rfft(mm * np.hanning(len(mm)))) ** 2
        f = np.fft.rfftfreq(len(mm), 1 / SR)
        k = (f > 25) & (f < 80)
        return float(f[k][np.argmax(s[k])])
    cands = [Hc["carrier"]] if "carrier" in Hc else Hc["carriers"]
    cs = [rd(p, "lowpass=f=120,lowpass=f=120", ss=2, t=4) for p in cands]
    fs = [f0(c) for c in cs]
    ci = int(np.argmin([abs(np.log(f / parts[0][0])) for f in fs]))
    print("carrier", cands[ci], "f0", [round(f, 1) for f in fs])
    w2 = np.hanning(int(0.1 * SR))
    w2 /= w2.sum()

    def tone(hz):
        c = flt(cs[ci], f"asetrate={SR * hz / fs[ci]:.1f},aresample={SR}")
        c = c / np.sqrt(conv(c.mean(1) ** 2, w2) + 1e-12)[:, None]
        return np.tile(c, (int(np.ceil(len(ee) / len(c))) + 1, 1))[:len(ee)]
    car = sum(a * tone(hz) for hz, a in parts)
    hw = np.hanning(SR // 2)
    car = car / np.sqrt(conv(car.mean(1) ** 2, hw / hw.sum()) + 1e-12)[:, None]
    hit = car * ee[:len(car), None]
    sw = np.zeros_like(bed)
    ts = []
    for p in Hc["at"]:
        one = np.zeros_like(bed)
        t = p["t"] if "t" in p else p["onset_at"] - on * 0.01
        ts.append(t)
        place(one, hit, t, 10 ** (p.get("db", 0) / 20))
        sw += one * (ramp(len(bed), *TAIL) if p.get("tail") else 1)
    b0, blen = Hc.get("body_window", [a0 + 1.0, 1.2])
    sat = flt(np.tanh(8 * sw), "highpass=f=90,lowpass=f=600")
    t0 = ts[0]
    span = (int((t0 + b0 - a0) * SR), int((t0 + b0 - a0 + blen) * SR))
    need = 10 ** (db(flt(rd(REF, ss=b0, t=blen), LOW)) / 10) - 10 ** (db(flt(sw[span[0]:span[1]], LOW)) / 10)
    sat *= 10 ** (db([max(need, 1e-9) ** 0.5]) / 20) / 10 ** (db(flt(sat[span[0]:span[1]], LOW)) / 20)
    bed += sw + sat * Hc.get("body_mix", 0.5)

fx = np.zeros_like(bed)
for s in C.get("sfx", []):
    place(fx, rd(s["file"]), s["t"], 10 ** (s.get("db", 0) / 20))
mix = bed + fx
gain = 10 ** (C.get("peak_db", -2.0) / 20) / np.abs(mix).max()
print("lift dB", round(20 * np.log10(gain), 2))
fade = np.ones((len(mix), 1))
k = int(0.03 * SR)
fade[-k:, 0] = np.linspace(1, 0, k)
fade[:int(0.005 * SR), 0] = np.linspace(0, 1, int(0.005 * SR))


def save(x, p):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s24le", p],
                   input=(x * fade * gain).astype(np.float32).tobytes(), check=True)


O = C["out"]
save(mix, O["mix"])
save(bed, O["bed"])
json.dump(dict(pad_pieces=[best[1] * 0.25, best[2] * 0.25], lift_db=20 * np.log10(gain), levels=T, sfx=C.get("sfx", [])), open(O["json"], "w"))
print("wrote", O["mix"], O["bed"])
