import argparse, os, shutil, subprocess, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("dur", type=float)
ap.add_argument("--tile", action="append", required=True)
ap.add_argument("--passes", default="")
ap.add_argument("--gain", action="append", default=[])
ap.add_argument("--fps", type=int, default=60)
a = ap.parse_args()
tiles = [dict(zip(("file", "map", "label"), (t.split("|") + ["", ""])[:3])) for t in a.tile]
for t in tiles:
    t["label"] = t["label"].replace(":", " ").replace("'", "").replace("\\", "")
    t["audio"] = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", t["file"]],
                                     capture_output=True, text=True).stdout.strip())
passes = [int(x) for x in a.passes.split(",")] if a.passes else [len(tiles) - 1]
gains = {int(g.split(":")[0]): float(g.split(":")[1]) for g in a.gain}
FF = next((p for p in [os.environ.get("FFMPEG"), "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "/usr/local/opt/ffmpeg-full/bin/ffmpeg"] if p and os.path.exists(p)), "ffmpeg")
has_text = "drawtext" in subprocess.run([FF, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
font = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans"], capture_output=True, text=True).stdout if shutil.which("fc-match") else ""
N, GAP = len(tiles), 14
TW = (1920 - GAP * (N + 1)) // N // 2 * 2


def segs(t):
    out, at = [], 0.0
    for p in [x for x in t["map"].split(",") if x]:
        span, t0 = p.split("@")
        s, e = (float(v) for v in span.split("-"))
        t0 = float(t0)
        if t0 > at + 1e-4:
            out.append(("gap", at, t0 - at))
        out.append(("seg", s, e - s))
        at = t0 + e - s
    if at < a.dur - 1e-4:
        out.append(("gap" if t["map"] else "seg", at if t["map"] else 0.0, a.dur - at))
    return out


def size(f):
    w, h = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", f],
                          capture_output=True, text=True).stdout.strip().split(",")[:2]
    return int(w), int(h)


T = tempfile.TemporaryDirectory()
tmp = T.name
ins, fc, vlab, alab = [], [], [], {}
for i, t in enumerate(tiles):
    ins += ["-i", t["file"]]
    w, h = size(t["file"])
    tw = min(TW, int(980 * w / h) // 2 * 2)
    th = int(tw * h / w) // 2 * 2
    t["w"], t["h"] = tw, th
    vs, as_, at, nxt = [], [], 0.0, None
    for k, (kind, s, d) in enumerate(segs(t)):
        n = round((at + d) * a.fps) - round(at * a.fps)
        at, d0 = at + d, d
        d = n / a.fps
        if kind == "seg":
            f0 = nxt[1] if nxt and abs(nxt[0] - s) < 1e-6 else round(s * a.fps)
            nxt = (s + d0, f0 + n)
        if n <= 0:
            continue
        if kind == "gap":
            fc.append(f"color=c=black:s={tw}x{th}:r={a.fps}:d={d:.6f}[g{i}_{k}]")
            fc.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{d:.6f}[ga{i}_{k}]")
            vs.append(f"[g{i}_{k}]")
            as_.append(f"[ga{i}_{k}]")
        else:
            fc.append(f"[{i}:v]fps={a.fps}:start_time=0,tpad=stop_mode=clone:stop=-1,trim=start_frame={f0}:end_frame={f0 + n},setpts=PTS-STARTPTS,scale={tw}:{th}:flags=lanczos,setsar=1[v{i}_{k}]")
            fc.append(f"[{i}:a]atrim={f0 / a.fps:.6f}:{(f0 + n) / a.fps:.6f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={d:.6f},atrim=0:{d:.6f},afade=t=in:d=0.02,afade=t=out:st={max(0, d - 0.02):.4f}:d=0.02[a{i}_{k}]"
                      if t["audio"] else f"anullsrc=r=48000:cl=stereo,atrim=0:{d:.6f}[a{i}_{k}]")
            vs.append(f"[v{i}_{k}]")
            as_.append(f"[a{i}_{k}]")
    fc.append("".join(vs) + f"concat=n={len(vs)}:v=1:a=0,settb=1/{a.fps},setpts=N/({a.fps}*TB)[tv{i}]")
    fc.append("".join(as_) + f"concat=n={len(as_)}:v=0:a=1,volume={gains.get(i, 0)}dB[ta{i}]")
fc.append(f"color=c=0x0b0b0c:s=1920x1080:r={a.fps}:d={a.dur}[bg0]")
last = "bg0"
for i, t in enumerate(tiles):
    x, y = GAP + i * (TW + GAP) + (TW - t["w"]) // 2, (1080 - t["h"]) // 2
    fc.append(f"[{last}][tv{i}]overlay={x}:{y}:shortest=1[bg{i + 1}]")
    last = f"bg{i + 1}"
    if has_text and t["label"]:
        fc.append(f"[{last}]drawtext=fontfile='{font}':expansion=none:text='{t['label']}':x={x}:y={y + t['h'] + 16}:fontsize=26:fontcolor=0x9aa4ad[{last}t]")
        last += "t"
picture = os.path.join(tmp, "pic.mp4")
subprocess.run([FF, "-nostdin", "-loglevel", "error", "-y"] + ins + ["-filter_complex", ";".join(fc), "-map", f"[{last}]"] +
               sum([["-map", f"[ta{i}]"] for i in range(N)], []) + ["-t", str(a.dur), "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
               "-pix_fmt", "yuv420p", "-c:a", "pcm_s24le", picture.replace(".mp4", ".mov")], check=True)
parts = []
for j, p in enumerate(passes):
    o = os.path.join(tmp, f"pass{j}.mp4")
    vf = []
    if has_text and len(passes) > 1:
        vf = ["-vf", f"drawtext=fontfile='{font}':expansion=none:text='Sound from {tiles[p]['label'] or p}':x=(w-tw)/2:y=150:fontsize=34:fontcolor=0xF7F7F7"]
    cv = ["-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(a.fps)] if vf else ["-c:v", "copy"]
    subprocess.run([FF, "-nostdin", "-loglevel", "error", "-y", "-i", picture.replace(".mp4", ".mov"), "-map", "0:v", "-map", f"0:a:{p}"] + vf +
                   cv + ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", o], check=True)
    parts.append(o)
open(os.path.join(tmp, "l.txt"), "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run([FF, "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "l.txt"), "-c", "copy", a.out], check=True)
T.cleanup()
print(a.out, subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "csv=p=0", a.out], capture_output=True, text=True).stdout.strip())
