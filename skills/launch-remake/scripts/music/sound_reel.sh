#!/usr/bin/env bash
set -euo pipefail
out=$1; secs=$2; hp=$3; shift 3
T=$(mktemp -d); i=0
trap 'rm -rf "$T"' EXIT
for a in "$@"; do
  f=${a%@*}; s=${a##*@}; [ "$f" = "$a" ] && s=0
  af="loudnorm=I=-20:TP=-2:LRA=11,afade=t=in:d=0.3,afade=t=out:st=$(python3 -c "print($secs-0.4)"):d=0.4,apad=pad_dur=1.5"
  [ "$hp" != 0 ] && af="highpass=f=$hp,highpass=f=$hp,$af"
  ffmpeg -nostdin -loglevel error -y -ss "$s" -t "$secs" -i "$f" -af "$af" -t "$(python3 -c "print($secs+1.5)")" -ar 44100 -ac 2 "$T/r$i.wav"
  echo "file 'r$i.wav'" >> "$T/l.txt"; i=$((i + 1))
done
ffmpeg -nostdin -loglevel error -y -f concat -safe 0 -i "$T/l.txt" -c:a pcm_s16le "$T/all.wav"
ffmpeg -nostdin -loglevel error -y -f lavfi -i color=c=black:s=320x180:r=5 -i "$T/all.wav" -shortest -c:v libx264 -tune stillimage -c:a aac -b:a 192k "$out"
rm -rf "$T"
python3 -c "
s=$secs+1.5
for k in range($i): print(f'track {k+1}: {int(k*s//60)}:{k*s%60:04.1f}-{int((k*s+$secs)//60)}:{(k*s+$secs)%60:04.1f}' + (' (reference)' if k==0 else ''))"
