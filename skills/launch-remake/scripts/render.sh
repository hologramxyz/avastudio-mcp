#!/usr/bin/env bash
set -euo pipefail
P=$(cd "$1" && pwd); O=$(cd "$(dirname "$2")" && pwd)/$(basename "$2"); Q=${4:-delivery}
X=$(cd "$(dirname "$0")" && pwd)
F=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['fps'])" "$P/build.json")
want=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['frames'])" "$P/build.json")
if [ -n "${3:-}" ] && [ "$3" != "$F" ]; then echo "the film was built at $F fps; rebuild it to render at $3 fps"; exit 1; fi
HF=(hyperframes); command -v hyperframes >/dev/null || HF=(npx --yes hyperframes@0.9.19)
for p in "${PY:-}" "$HOME/.launch-remake/venv/bin/python" "$HOME/venv/bin/python" python3; do [ -n "$p" ] && command -v "$p" >/dev/null && { PY=$p; break; }; done
"$PY" -c "import cv2, numpy" 2>/dev/null || { echo "$PY has no numpy or OpenCV: run doctor.sh"; exit 1; }
grep -q "<video" "$P"/compositions/*.html && export PRODUCER_FORCE_SCREENSHOT=true
export HYPERFRAMES_RENDER_LOCK=off HYPERFRAMES_RENDER_DETACHED=1
L=$(mktemp -d)
CH=
trap 'rm -rf "$L"' EXIT
trap '[ -n "$CH" ] && kill -TERM "$CH" 2>/dev/null; wait; exit 143' INT TERM
cd "$P"
attempt() {
  local s=$SECONDS mode n
  "${HF[@]}" render --quality "$Q" --fps "$F" "$@" --output "$O" > "$L/render.log" 2>&1 </dev/null &
  CH=$!
  wait "$CH" || { CH=; tail -n 20 "$L/render.log"; return 1; }
  CH=
  mode=$(grep -o -E "(hardware|software) gpu" "$L/render.log" | tail -1 || true)
  n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 "$O")
  echo "$O: $n of $want frames, $(( SECONDS - s )) s, ${mode:-gpu unknown}, $*"
  [ "$n" = "$want" ] || { echo "frame count is wrong"; return 1; }
  "$PY" "$X/qa.py" "$O" "$P" "${O%.*}-qa" > "$L/qa.txt" 2>&1 || { cat "$L/qa.txt"; return 1; }
  cp "$L/qa.txt" "${O%.*}-qa/qa.txt"
  grep "^one-frame flashes:" "$L/qa.txt" > "$L/flash.txt"
  grep -E "^(jumps away from cuts|blank or near-blank)" "$L/qa.txt" || true
  cat "$L/flash.txt"
  echo "frame QA images and report: ${O%.*}-qa"
}
clean() { grep -q "flashes: none" "$L/flash.txt"; }
C=$(nproc 2>/dev/null || sysctl -n hw.ncpu)
G=$([ "$(uname -s)" = Darwin ] || nvidia-smi -L >/dev/null 2>&1 && echo 1 || echo $((C > 1 ? C - 1 : 1)))
W=${5:-${RENDER_WORKERS:-$G}}
attempt --workers "$W" || exit 1
clean && exit 0
mv "$L/flash.txt" "$L/flash-first.txt"
if [ "$W" != 1 ]; then
  attempt --workers 1 || exit 1
  clean && exit 0
  cmp -s "$L/flash.txt" "$L/flash-first.txt" && same=1
fi
if [ -z "${same:-}" ]; then
  attempt --workers auto --no-browser-gpu || exit 1
  clean && exit 0
fi
echo "flashes remain after the retries: look at these frames in $O; go on only if the spec plans them"
exit 3
