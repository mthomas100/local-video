#!/bin/zsh
# keysheet.sh <film name> <out dir> [--take LABEL] <scene>... — six frames per clip (3x2) for the auditor's own answer
# key, written BEFORE reading the director's verdicts (2026-09-26; moved into the repo 2026-09-27). With --take the
# sheet is <out>/scene-N-LABEL.png, so a redo take never overwrites take 1's sheet. CPU only; safe during a render.
set -u
F=~/Videos/vidgen/$1; K=$2; shift 2; T=""
[ "${1:-}" = --take ] && { T=-$2; shift 2; }
mkdir -p $K
for n in "$@"; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $F/scene-$n.mp4)
  ffmpeg -hide_banner -loglevel error -y -i $F/scene-$n.mp4 -vf "fps=6/$d,scale=300:-2,tile=3x2" -frames:v 1 $K/scene-$n$T.png && echo $K/scene-$n$T.png
done
