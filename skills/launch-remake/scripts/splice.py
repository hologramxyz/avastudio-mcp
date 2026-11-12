import json, os, subprocess, sys

full, part, proj, out = sys.argv[1:5]
B = json.load(open(os.path.join(proj, "build.json")))
fps, (a, b) = B["fps"], B["window"]
k0, n = round(a * fps), B["frames"]


def frames(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", f],
                       capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def info(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", f],
                       capture_output=True, text=True, check=True)
    w, h, rate = r.stdout.strip().split(",")
    n, d = rate.split("/")
    return int(w), int(h), round(int(n) / int(d), 3)


fi, pi = info(full), info(part)
if fi != pi or abs(fi[2] - fps) > 0.01:
    sys.exit(f"size or frame rate differ: film {fi[0]}x{fi[1]} at {fi[2]} fps, window {pi[0]}x{pi[1]} at {pi[2]} fps, window build {fps} fps; build both at the same --fps")
total, got = frames(full), frames(part)
if got != n:
    sys.exit(f"{part}: {got} frames, the window build has {n}")
if k0 + n > total:
    sys.exit(f"the window ends at frame {k0 + n}, past the film's {total} frames")
segs, labels = [], []
if k0:
    segs.append(f"[0:v]trim=end_frame={k0},setpts=PTS-STARTPTS[a]"); labels.append("[a]")
segs.append("[1:v]setpts=PTS-STARTPTS[b]"); labels.append("[b]")
if k0 + n < total:
    segs.append(f"[0:v]trim=start_frame={k0 + n},setpts=PTS-STARTPTS[c]"); labels.append("[c]")
graph = ";".join(segs) + f";{''.join(labels)}concat=n={len(labels)}:v=1:a=0,setpts=N/({fps}*TB),fps={fps}[v]"
tmp = out + ".tmp.mp4"
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", full, "-i", part, "-filter_complex", graph, "-map", "[v]",
                "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p", tmp], check=True)
if frames(tmp) != total:
    os.remove(tmp)
    sys.exit("the spliced film has the wrong frame count")
os.replace(tmp, out)
print(f"{out}: frames {k0}-{k0 + n - 1} ({a:.3f}-{b:.3f} s) replaced, {total} frames")
