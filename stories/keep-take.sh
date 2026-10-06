#!/bin/zsh
# keep-take.sh <project-file> <scene> — put the previous take of a redone scene back (2026-09-27; the keep_take tool).
# The current take's files move into a new redo-M/ (nothing is deleted); the latest earlier take's files are copied
# back from their redo-K/; the film is re-stitched by story.sh (ONLY=<scene> renders nothing: the scene exists).
set -u
proj=$1; s=$2; [ -f $proj ] || { echo "no project $proj"; exit 2; }
name=$(grep -m1 '^NAME=' $proj | cut -d= -f2 | cut -d';' -f1)
OUT=~/Videos/vidgen/$name
pgrep -f "ltx-2-mlx generat[e]" >/dev/null && { echo "a render is running; wait"; exit 1; }
k=$(ls -d $OUT/redo-* 2>/dev/null | sed 's/.*redo-//' | sort -n | while read x; do [ -s $OUT/redo-$x/scene-$s.mp4 ] && echo $x; done | tail -1)
[ -n "$k" ] || { echo "scene $s has no previous take in $OUT/redo-*/"; exit 1; }
m=1; while [ -d $OUT/redo-$m ]; do m=$((m+1)); done; mkdir -p $OUT/redo-$m
for f in scene-$s.mp4 scene-$s.json still-$s.png still-$s.txt still-$s.key; do [ -e $OUT/$f ] && mv $OUT/$f $OUT/redo-$m/; done
[ -e $OUT/$name.mp4 ] && mv $OUT/$name.mp4 $OUT/redo-$m/
for f in scene-$s.mp4 scene-$s.json still-$s.png still-$s.txt still-$s.key; do [ -e $OUT/redo-$k/$f ] && cp -p $OUT/redo-$k/$f $OUT/; done
echo "scene $s: kept the take from redo-$k; the replaced take is in redo-$m"
ONLY="$s" zsh ~/repos/local-video/stories/story.sh $proj | tail -2
