#!/bin/zsh
# ice-queen-90s.sh — a 90-second storyboard as six 15-second scenes (2026-09-22).
# LTX-2.5 caps one generation at 20 s, so a long piece is several scenes with the SAME
# character/setting paragraph and the SAME seed (continuity), stitched with ffmpeg.
# Re-runnable: scenes that already exist are skipped; delete one to redo it.
set -u
STYLE=${STYLE:-real}                       # real (live-action) | cartoon (the first draft's look)
OUT=~/Videos/vidgen/ice-queen-90s-$STYLE; mkdir -p $OUT
SEED=${SEED:-7}; SIZE=${SIZE:-480p}; SECS=15; MODE=${MODE:-}   # MODE=--quality for the final
# Continuity: every run is independent and remembers nothing, so later scenes are anchored
# to a REFERENCE FRAME pulled from an earlier scene (LTX image-to-video keeps that face).
# bin/pick-face-frame samples scene 1 every 0.5 s and lets macOS Vision choose the frame
# with the best single face -> ref-queen.png (anchors scenes 2-4); the best two-face frame
# of scene 4 -> ref-pair.png (queen + third prince, anchors scenes 5-6). A contact sheet
# of every candidate sits next to each PNG; replace the PNG with any frame you prefer and
# rerun. Strength < 1 guides instead of freezing the first frame. Untested value; tune it.
REF_STRENGTH=${REF_STRENGTH:-0.85}
# The picker finds the biggest sharp face, not "the queen". So it is a proposal: the frame
# and the contact sheet open, and a human confirms (Enter) or types another frame number
# from the sheet (numbered left-to-right, top-to-bottom, one every 0.5 s). CONFIRM=0 skips.
grab() {
  local video=$1 out=$3 want=${4:-1}
  ~/repos/local-video/bin/pick-face-frame $video $out $want
  [ "${CONFIRM:-1}" = 0 ] && return
  if [ "${CONFIRM:-1}" = agent ]; then
    # Agent-in-the-loop: an assistant (Claude Code / pi) reads the PNG + sheet with its own
    # eyes and writes ${out%.png}.answer: empty = accept, a frame number = use that frame.
    local ans_file="${out%.png}.answer"; rm -f $ans_file
    echo "WAITING_FOR_ANSWER $ans_file"
    until [ -f $ans_file ]; do sleep 2; done
    local ans=$(cat $ans_file)
    if [[ $ans == <-> ]]; then
      ffmpeg -hide_banner -loglevel error -y -ss $(( (ans-1)/2 )).$(( ((ans-1)%2)*5 )) -i $video -frames:v 1 $out
      echo "reference replaced with frame $ans"
    fi
    return
  fi
  open $out "${out%.png}-sheet.png"
  while true; do
    printf "Is %s the right face(s)? [Enter = yes, or frame number from the sheet, q = quit]: " ${out:t}
    read -r ans
    case $ans in
      "") return ;;
      q) echo "stopped by user"; exit 1 ;;
      <->) ffmpeg -hide_banner -loglevel error -y -ss $(( (ans-1)/2 )).$(( ((ans-1)%2)*5 )) -i $video -frames:v 1 $out && open $out ;;
      *) echo "Enter, a number, or q" ;;
    esac
  done
}

if [ $STYLE = cartoon ]; then
BIBLE='Soft pastel Disney-style animated fairy tale, cinematic and pretty, gentle diffused light. The Ice Queen: pale skin, very long straight blonde hair, a slender silver crystal gown, a small crystal crown. Setting: a castle hall made of ice and crystal, one crystal chandelier, a few frozen statues and frozen flowers, elegant and uncluttered. Camera stays close, medium shots and close-ups, never far away.'
else
BIBLE='Photorealistic live-action fantasy film, real human actors, shot on 35mm with anamorphic lenses, shallow depth of field, natural skin texture and pores, soft cool window light with warm practical candlelight, subtle restrained performances. The Ice Queen: a woman in her late twenties, pale skin, very long straight platinum-blonde hair, a fitted silver gown of embroidered crystal, a delicate crystal crown. Setting: a great hall carved from ice and crystal, one crystal chandelier, a few ice statues and frost-covered flowers, elegant and uncluttered. Every character is an adult. Medium shots and close-ups, never wide.'
fi

typeset -a SCENES
SCENES=(
"Close-up on the Ice Queen's calm, cold face on her crystal throne, then a slow pan circling her at medium distance past frozen flowers and the chandelier. Soft shimmering ambience, a faint crystalline hum."
"An adult man, a prince in a dark velvet coat, kneels and opens a box holding a glittering diamond necklace. Cut to a close-up: she studies it, a flicker of boredom crosses her face, and she dismisses him with the smallest turn of her hand; cut back as he bows and withdraws. Footsteps on ice, the box closing, a cold sigh."
"A second adult man, a bearded prince in a red and gold doublet, drags forward a chest overflowing with gold coins. Cut between his hopeful face and hers: she looks at the gold, then away, faintly disappointed, and waves him off; he retreats. Coins clinking, an icy silence."
"A third adult man, a young prince in a tall top hat, steps up, sweeps the hat off, and pulls out a white dove, then a rabbit. Cut to a close-up of the Ice Queen: her eyes widen, her composure cracks, and she breaks into genuine laughter. A dove's wingbeats, her surprised laugh."
"The prince bows and offers his hand; the Ice Queen hesitates, then takes it, and they begin to waltz across the ice hall. The camera circles them slowly, then cuts in close on their faces, shy smiles turning to laughter. A warm swelling waltz, laughter, the whisper of her gown."
"As they dance, the ice around them melts into sparkling water and real flowers rise through the melting floor; her crystal crown melts away and her silver gown warms into a sunny yellow dress as golden sunlight floods the hall. Close on the two of them laughing, spinning, eyes locked. Dripping water, birdsong, a joyful orchestral swell."
)

i=0
for s in "${SCENES[@]}"; do
  i=$((i+1)); f=$OUT/scene-$i.mp4
  if [ -s $f ]; then echo "scene $i exists, skipping"; continue; fi
  echo "=== scene $i / ${#SCENES[@]}"
  typeset -a ref; ref=()
  if [ $i -ge 2 ] && [ $i -le 4 ]; then
    [ -s $OUT/ref-queen.png ] || grab $OUT/scene-1.mp4 - $OUT/ref-queen.png 1
    ref=(-- --image $OUT/ref-queen.png 0 $REF_STRENGTH)
  elif [ $i -ge 5 ]; then
    [ -s $OUT/ref-pair.png ] || grab $OUT/scene-4.mp4 - $OUT/ref-pair.png 2
    ref=(-- --image $OUT/ref-pair.png 0 $REF_STRENGTH)
  fi
  vidgen --no-open $MODE --seconds $SECS --size $SIZE --seed $SEED -o $f "$BIBLE $s" "${ref[@]}" || { echo "scene $i failed"; exit 1; }
done

ls $OUT/scene-*.mp4 | sort -V | sed "s|^|file '|; s|\$|'|" > $OUT/list.txt
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $OUT/list.txt -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k $OUT/ice-queen-90s.mp4 \
  && echo "stitched → $OUT/ice-queen-90s.mp4" && open $OUT/ice-queen-90s.mp4
