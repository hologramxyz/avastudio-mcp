#!/usr/bin/env bash
set -euo pipefail
pic=$1; pss=$2; aud=$3; ass=$4; dur=$5; hp=$6; gain=$7; out=$8
af="volume=${gain}dB,alimiter=limit=0.9"
[ "$hp" != 0 ] && af="highpass=f=$hp,highpass=f=$hp,$af"
ffmpeg -nostdin -loglevel error -y -ss "$pss" -t "$dur" -i "$pic" -ss "$ass" -t "$dur" -i "$aud" -map 0:v -map 1:a \
  -vf "scale='if(gte(iw,ih),960,-2)':'if(gte(iw,ih),-2,960)',fps=30" -af "$af" -c:v libx264 -crf 26 -maxrate 3M -bufsize 6M -preset veryfast -c:a aac -b:a 192k -t "$dur" "$out"
ffprobe -v error -show_entries format=duration,size -of csv=p=0 "$out"
