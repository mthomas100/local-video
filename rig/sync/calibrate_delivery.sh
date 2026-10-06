#!/bin/zsh
# calibrate_delivery.sh — the delivery meter on RAVDESS known answers (2026-09-27): per actor 1-4, the four neutral
# takes and one strong take (repetition 1) of happy, sad, angry and fearful for both sentences. Output JSONL with the
# RAVDESS code in "ravdess" (modality-channel-emotion-intensity-statement-repetition-actor).
R=~/datasets/ravdess; O=~/Videos/vidgen/sync-cal/delivery-ravdess.jsonl; : > $O
for a in 01 02 03 04; do
  for f in $R/Actor_$a/01-01-01-01-0[12]-0[12]-$a.mp4 $R/Actor_$a/01-01-0[3456]-02-0[12]-01-$a.mp4; do
    [ -e $f ] || continue
    st=${${f:t}:12:2}; line=$([ $st = 01 ] && echo "Kids are talking by the door" || echo "Dogs are sitting by the door")
    ~/repos/local-video/rig/sync/delivery.py --line "$line" $f 2>/dev/null | grep '^{' | python3 -c "import json,sys; r=json.loads(sys.stdin.read()); r['ravdess']='${${f:t}%.mp4}'; print(json.dumps(r))" >> $O
  done
done
echo done > $O.done
