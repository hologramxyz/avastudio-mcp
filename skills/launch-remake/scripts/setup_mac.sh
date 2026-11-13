#!/usr/bin/env bash
set -euo pipefail
command -v brew >/dev/null || { echo "Homebrew is needed first: https://brew.sh"; exit 1; }
command -v ffmpeg >/dev/null || brew install ffmpeg
[ -x "$(brew --prefix)/opt/ffmpeg-full/bin/ffmpeg" ] || brew install ffmpeg-full
major=$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0)
if [ "${major:-0}" -lt 22 ]; then brew install node@22 && brew link --overwrite --force node@22; fi
npm install -g hyperframes@0.9.19 puppeteer-core >/dev/null 2>&1
hyperframes browser ensure >/dev/null
V=${LR_VENV:-$HOME/.launch-remake/venv}
[ -x "$V/bin/python" ] || python3 -m venv "$V"
"$V/bin/pip" -q install numpy opencv-python-headless
PY="$V/bin/python" bash "$(cd "$(dirname "$0")" && pwd)/doctor.sh"
