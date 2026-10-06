#!/bin/zsh
# redo.sh <project-file> <scene>... — re-render the given scenes of a film (2026-09-23).
# Moves each scene's mp4/json, any reference picked from it, and the stitched film into
# $OUT/redo-N/ (nothing is deleted), then reruns story.sh with ONLY=<those scenes>, so nothing else
# renders even when other scenes are missing (a paused film), and it re-stitches only a complete film.
# Refuses to start while another render is running.
set -u
# One GPU lock for the Mac (2026-10-04, ~/repos/local-rig/docs/hold.md): queue for it instead of refusing; under
# redo_scenes this joins the tool's hold (HOLD_ID).
if [ -z "${HOLD_ID:-}" ] && command -v hold >/dev/null; then exec hold run --kind render --reason "redo ${${1:t}:r} ${*[2,-1]}" -- zsh $0 "$@"; fi
proj=$1; shift; [ -f $proj ] || { echo "no project $proj"; exit 2; }
name=$(grep -m1 '^NAME=' $proj | cut -d= -f2 | cut -d';' -f1)
OUT=~/Videos/vidgen/$name
pgrep -f "ltx-2-mlx generat[e]" >/dev/null && { echo "a render is running; wait"; exit 1; }
n=1; while [ -d $OUT/redo-$n ]; do n=$((n+1)); done; mkdir -p $OUT/redo-$n
for s in "$@"; do mv $OUT/scene-$s.mp4 $OUT/scene-$s.json $OUT/ref-from-$s.png $OUT/ref-from-$s-sheet.png $OUT/still-$s.png $OUT/still-$s.txt $OUT/still-$s.key $OUT/redo-$n/ 2>/dev/null
  # the sync gate's verdict, exception and retakes of that take go with it (2026-09-27)
  mv $OUT/sync-$s.json $OUT/sync-accept-$s.json $OUT/takes/scene-$s-try*(N) $OUT/takes/sync-$s-try*(N) $OUT/redo-$n/ 2>/dev/null; done
mv $OUT/$name.mp4 $OUT/redo-$n/ 2>/dev/null
echo "redo $name scenes $* (previous takes in $OUT/redo-$n)"
ONLY="$*" zsh ~/repos/local-video/stories/story.sh $proj
