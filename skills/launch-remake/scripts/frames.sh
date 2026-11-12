#!/bin/bash
set -euo pipefail
v=$1
if [ "$2" = strip ]; then
  r=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v" | python3 -c "import math,sys; print(math.ceil((float(sys.stdin.read()) * 3 + 1) / 6))")
  ffmpeg -loglevel error -y -i "$v" -vf "fps=3,scale=400:-1,tile=6x$r" -frames:v 1 "$3"
  echo "$3"; exit 0
elif [ "$3" = band ]; then
  ffmpeg -loglevel error -y -ss "$2" -i "$v" -frames:v 1 -vf "crop=w=min(1000\,iw):h=min(420\,ih):x=min(600\,iw-ow):y=0,colorlevels=rimax=0.38:gimax=0.38:bimax=0.38" "$4"
else
  f=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$v")
  n=$(python3 -c "import math; print(math.ceil(float('$3') * $f / 6))")
  ffmpeg -loglevel error -y -ss "$2" -t "$3" -i "$v" -vf "scale=400:-1,tile=6x$n" -frames:v 1 "$4"
fi
echo "$4"
