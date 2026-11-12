#!/usr/bin/env bash
set -uo pipefail
bad=0
need() { echo "missing: $1"; bad=1; }
major=$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/')
[ "${major:-0}" -ge 22 ] && echo "node $(node -v)" || need "Node 22 or newer"
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && echo "ffmpeg $(ffmpeg -version | head -1 | cut -d' ' -f3)" || need "ffmpeg and ffprobe"
FF=ffmpeg; for p in "${FFMPEG:-}" /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg /usr/local/opt/ffmpeg-full/bin/ffmpeg; do [ -n "$p" ] && [ -x "$p" ] && { FF=$p; break; }; done
"$FF" -hide_banner -filters 2>/dev/null | grep drawtext >/dev/null || echo "note: no ffmpeg with drawtext, so side-by-side labels are left out (Mac: brew install ffmpeg-full; sbs.py finds it)"
v=$(command -v hyperframes >/dev/null && hyperframes --version 2>/dev/null | tail -1); [ -n "$v" ] && echo "hyperframes $v" || need "HyperFrames (npm install -g hyperframes@0.9.19)"
NODE_PATH=$(npm root -g) node -e "require('puppeteer-core')" 2>/dev/null && echo "puppeteer-core ok" || need "puppeteer-core (npm install -g puppeteer-core)"
for p in "${PY:-}" "$HOME/.launch-remake/venv/bin/python" "$HOME/venv/bin/python"; do
  [ -n "$p" ] && [ -x "$p" ] && "$p" -c "import numpy, cv2" 2>/dev/null && { echo "PY=$p"; PYOK=1; break; }
done
[ -n "${PYOK:-}" ] || need "a Python venv with numpy and opencv-python-headless (run the setup script)"
C=${CHROME:-}; for p in /usr/bin/google-chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do [ -z "$C" ] && [ -x "$p" ] && C=$p; done
[ -z "$C" ] && command -v hyperframes >/dev/null && C=$(hyperframes browser path 2>/dev/null | tail -1)
[ -n "$C" ] && [ -x "$C" ] && echo "chrome $C" || need "Chrome (hyperframes browser ensure)"
case "$(uname -s)" in
  Darwin) echo "gpu: Metal" ;;
  Linux) nvidia-smi -L >/dev/null 2>&1 && echo "gpu: NVIDIA (render.sh checks it on the first render)" || echo "gpu: none, renders use SwiftShader on the CPU and take several times longer" ;;
esac
free=$(df -Pk . | awk 'NR==2{print int($4/1048576)}')
[ "$free" -ge 8 ] && echo "disk: $free GB free" || need "8 GB free disk here (a delivery render keeps about 2.3 MB per frame while it runs); $free GB free"
exit $bad
