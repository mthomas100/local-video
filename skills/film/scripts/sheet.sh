#!/bin/zsh
# sheet.sh <NAME> <scene>... — contact sheet of the named scenes of a film, one row per scene,
# frames spread evenly over each clip. Writes ~/Videos/vidgen/<NAME>/sheet-<scenes>.png and prints
# the path. CPU only (ffmpeg); safe to run during a render.
#
# Frames per row (2026-09-24): six when any clip in the sheet is longer than 10 s, else four, taken
# evenly over each clip's own duration. It used to take one frame every 2.5 s into six tiles, which
# fits a 15 s scene but leaves an 8 s shot with four frames and two blank tiles. Frame width: 290 px
# for portrait; for landscape the row is about 1740 px (435 px a frame at four), so a 720p shot is
# still legible after the rig scales the sheet to 1400 px for the model.
set -eu
name=$1; shift; dir=~/Videos/vidgen/$name
[ $# -gt 0 ] || { echo "usage: sheet.sh <NAME> <scene>..."; exit 2; }
typeset -a durs
maxd=0
for s in "$@"; do
  f=$dir/scene-$s.mp4; [ -s $f ] || { echo "missing $f" >&2; exit 1; }
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $f); d=${d:-15}
  durs+=($d); (( d > maxd )) && maxd=$d
done
(( maxd > 10.5 )) && k=6 || k=4
wh=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x $dir/scene-$1.mp4)
if (( ${wh%x*} > ${wh#*x} )); then w=$(( 1740 / k )); else w=290; fi
inputs=(); filter=""; labels=""; i=0
for s in "$@"; do
  f=$dir/scene-$s.mp4; i=$((i+1))
  inputs+=(-i $f); filter+="[$((i-1)):v]fps=${k}/${durs[$i]},scale=${w}:-2,tile=${k}x1[r$i];"; labels+="[r$i]"
done
out=$dir/sheet-${(j:-:)@}.png
# vstack needs two or more inputs; a single scene is just its own row (found by the rig's smoke test, 2026-09-23)
if [ $i -eq 1 ]; then filter="[0:v]fps=${k}/${durs[1]},scale=${w}:-2,tile=${k}x1"; else filter="${filter}${labels}vstack=inputs=$i"; fi
ffmpeg -hide_banner -loglevel error -y "${inputs[@]}" -filter_complex "$filter" -frames:v 1 $out
echo $out
