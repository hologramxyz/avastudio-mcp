import json, os, subprocess, sys
import cv2
import numpy as np

film, proj, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
B = json.load(open(os.path.join(proj, "build.json")))
fps = B["fps"]
c = cv2.VideoCapture(film)
luma, peak, flat, d, prev = [], [], [], [], None
while True:
    ok, f = c.read()
    if not ok:
        break
    g = cv2.cvtColor(cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    d.append(0.0 if prev is None else float(cv2.absdiff(g, prev).mean()))
    prev = g
    luma.append(float(g.mean()))
    peak.append(int(g.max()))
    lo, hi = np.percentile(g, [0.5, 99.5])
    flat.append(hi - lo < 16)
n = len(luma)
if n == 0:
    sys.exit(f"{film}: no frames (the render failed or is empty)")
print(f"frames {n} of {B['frames']}" + ("" if n == B["frames"] else "  WRONG"))
d = np.array(d)
cutf = {int(np.floor(t * fps)) + 1 for t in B["cuts"]}
for t in B["cuts"]:
    k = int(np.floor(t * fps)) + 1
    if k >= n:
        print(f"cut {t:.4f}: MISSING, frame {k} is past the last frame {n - 1}")
        continue
    print(f"cut {t:.4f}: jump at frame {k} = {d[k]:.2f} (neighbours {d[k - 1]:.2f}, {d[min(n - 1, k + 1)]:.2f})")
calm = np.median(d[1:])
odd = [k for k in range(2, n - 1) if k not in cutf and d[k] > max(2.2, 6 * calm) and d[k] > 3 * max(d[k - 1], d[k + 1])]
print("jumps away from cuts:", [(k, round(k / fps, 3), round(d[k], 2)) for k in odd[:12]] or "none")
a = np.array(luma)
flash = [k for k in range(1, n - 1) if (abs(a[k] - a[k - 1]) > 1.5 and abs(a[k] - a[k + 1]) > 1.5 and abs(a[k + 1] - a[k - 1]) < 1.0)
         or (min(peak[k - 1], peak[k + 1]) >= 12 and peak[k] < 0.5 * min(peak[k - 1], peak[k + 1]))]
flash = [k for k in flash if not (k in cutf and k + 1 in cutf)]
print("one-frame flashes:", [(k, round(k / fps, 3)) for k in flash] or "none")
empty, k = [], 0
while k < n:
    if flat[k]:
        j = k
        while j + 1 < n and flat[j + 1]:
            j += 1
        empty.append((round(k / fps, 3), round(j / fps, 3)))
        k = j
    k += 1
print("blank or near-blank frame runs (s), look at each:", empty or "none")


def grab(k):
    c.set(cv2.CAP_PROP_POS_FRAMES, k)
    ok, f = c.read()
    f = cv2.resize(f, (320, 180)) if ok else np.zeros((180, 320, 3), np.uint8)
    cv2.putText(f, f"{k} {k / fps:.3f}", (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return f


for i, t in enumerate(B["cuts"]):
    k = int(np.floor(t * fps)) + 1
    if k >= n:
        continue
    fr = [grab(j) for j in range(max(0, k - 5), min(n, k + 7))]
    while len(fr) % 6:
        fr.append(np.zeros_like(fr[0]))
    cv2.imwrite(os.path.join(out, f"cut-{i + 1}.jpg"), cv2.vconcat([cv2.hconcat(fr[r:r + 6]) for r in range(0, len(fr), 6)]))
fr = [grab(int(k)) for k in np.arange(0, n, fps / 2)]
while len(fr) % 8:
    fr.append(np.zeros_like(fr[0]))
cv2.imwrite(os.path.join(out, "strip.jpg"), cv2.vconcat([cv2.hconcat(fr[r:r + 8]) for r in range(0, len(fr), 8)]))
print("wrote", out)
