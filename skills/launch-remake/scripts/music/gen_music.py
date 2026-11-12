import json, os, sys, time, uuid, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ["ELEVEN_LABS_API_KEY"]
out = sys.argv[2]
os.makedirs(out, exist_ok=True)


def compose(j):
    body = dict(prompt=j["description"], music_length_ms=int(j["secs"] * 1000), model_id=j.get("model", "music_v2_5"), force_instrumental=True)
    return urllib.request.Request("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192", data=json.dumps(body).encode(),
                                  headers={"xi-api-key": KEY, "Content-Type": "application/json"}, method="POST")


def run(j):
    b = uuid.uuid4().hex
    parts = []

    def field(n, v):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode())
    v = j.get("video", "")
    if v:
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="videos"; filename="{os.path.basename(v)}"\r\nContent-Type: video/mp4\r\n\r\n'.encode() + open(v, "rb").read() + b"\r\n")
    field("description", j["description"])
    for t in j.get("tags", []):
        field("tags", t)
    field("model_id", j.get("model", "music_v2_5"))
    field("use_audio_as_reference", "true" if j.get("audio_ref", True) else "false")
    field("add_sfx", "false")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request("https://api.elevenlabs.io/v1/music/video-to-music?output_format=mp3_44100_192", data=b"".join(parts),
                                 headers={"xi-api-key": KEY, "Content-Type": f"multipart/form-data; boundary={b}"}, method="POST") if v else compose(j)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            data = r.read()
            h = {k.lower(): v for k, v in r.headers.items()}
        p = os.path.join(out, j["name"] + ".mp3")
        open(p, "wb").write(data)
        rec = dict(name=j["name"], ok=True, bytes=len(data), secs=round(time.time() - t0), cost=h.get("character-cost"), song_id=h.get("song-id"), job=j)
    except urllib.error.HTTPError as e:
        rec = dict(name=j["name"], ok=False, code=e.code, err=e.read()[:400].decode(errors="replace"), job=j)
    except Exception as e:
        rec = dict(name=j["name"], ok=False, err=str(e)[:300], job=j)
    open(os.path.join(out, "receipts.jsonl"), "a").write(json.dumps(rec) + "\n")
    print({k: v for k, v in rec.items() if k != "job"}, flush=True)
    return rec


with ThreadPoolExecutor(4) as p:
    list(p.map(run, json.load(open(sys.argv[1]))))
