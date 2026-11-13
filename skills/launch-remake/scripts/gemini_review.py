import base64, json, os, sys, urllib.request, urllib.error
key = os.environ["GEMINI_API_KEY"]
video, prompt_file = sys.argv[1], sys.argv[2]
fps = float(sys.argv[3]) if len(sys.argv) > 3 else 10
model = sys.argv[4] if len(sys.argv) > 4 else "gemini-3.1-pro-preview"
data = base64.b64encode(open(video, "rb").read()).decode()
body = {"contents": [{"role": "user", "parts": [
    {"inlineData": {"mimeType": "video/mp4", "data": data}, "videoMetadata": {"fps": fps}},
    {"text": open(prompt_file).read()}]}],
    "generationConfig": {"temperature": 0.4}}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                             data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
try:
    with urllib.request.urlopen(req, timeout=900) as r:
        out = json.load(r)
    print("".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"]))
except urllib.error.HTTPError as e:
    print("ERR", e.code, e.read()[:600].decode(errors="replace").replace(key, "[redacted]"), file=sys.stderr)
    sys.exit(1)
