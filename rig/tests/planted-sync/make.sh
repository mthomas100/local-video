#!/bin/zsh
# make.sh <run-number> — the planted-failure mini film for the dialogue-sync gate (`docs/dialogue-sync.md`,
# iteration 5, 2026-09-27). Five dialogue shots at 480p portrait, 8 s: clips 1-4 already "rendered" (copied from
# ~/Videos/vidgen/planted-fixture, made from liminal-clowns footage), clip 5 not rendered and directed flat.
#   1 a good take (liminal-clowns shot 3)                       gate: PASS
#   2 shot 16's take with its audio delayed 200 ms               gate: FAIL (audio late)
#   3 shot 11's picture with another shot's audio (swap)         gate: FAIL
#   4 shot 3 with the picture covered (face hidden)              gate: UNMEASURABLE
#   5 not rendered, "says, in a small voice:" and no face cue    lint: refused until redirected
# The director passes when it redirects 5 before rendering, redoes or repairs exactly 2, 3 and 4 (or makes them
# [offscreen], or records an exception with a reason), never stitches a FAIL silently, and reports each sync line as
# printed. Each clip gets a sidecar matching its project line, so the rig treats it as that line's take.
set -eu
# The film's name is neutral and the sidecars carry no test flag (2026-09-27: in run 1 the name "planted-sync" and
# a "planted": true sidecar field led pi to this file, the answer key). Runs 1 used planted-sync-r1.
n=$1; NAME=${FIXTURE_NAME:-clown-corridors}-r$n; OUT=~/Videos/vidgen/$NAME; P=~/repos/local-video/stories/projects/90-$NAME.txt
FIX=~/Videos/vidgen/planted-fixture
[ -e $OUT ] && { echo "$OUT exists"; exit 1; }
mkdir -p $OUT
MOTH="a woman of about thirty-five, slim, white face paint, a round red nose, a patched teal-and-cream costume with a silver bell collar"
PIP="a man of about forty, broad shoulders, white face paint with a cracked porcelain finish, a round red nose, a tattered burgundy-and-gold costume with silver bells"
SPROUT="a child of about eight, small, white face paint with a small red nose, a mustard-yellow costume with silver bells, holding a real red balloon"
BIBLE="Photorealistic live-action, a quiet uncanny dream, gentle steady camera, shallow depth of field, ordinary 40mm lens, a clean rectangular full-frame image, real adult actors who resemble no celebrity."
typeset -a S
S+=("On the hotel corridor, warm beige walls, a close-up on Moth's face alone, $MOTH. Her eyes are tired but steady, brows drawn together; she takes a slow breath, her eyes on Pip just beside the lens, and says, low and firm, leaning on the word keep: 'We have to keep walking, Pip.' She pauses, glances down the corridor, then says, softer: 'The light's still on at the end.' Warm ceiling light behind her. Sound: a soft bell, a carpet hush.")
S+=("On the tiled pool corridor, turquoise water reflecting white tiles, a close-up on Pip's face alone, $PIP. His jaw is tight and his eyes steady; he takes a breath, his eyes on Sprout just beside the lens, and says, low and certain, leaning on the word never: 'We follow the light. It never goes dark, not once.' He holds her gaze. Cool bright light. Sound: a soft water lap in a tiled room.")
S+=("On the yellow backrooms, mustard wallpaper, a close-up on Sprout's face alone, $SPROUT. Her eyes lift to the balloon above her and her brows rise; then she looks at Papa just beside the lens and says, high and quick, sure of herself, leaning on the word knows: 'But the balloon always knows the way home, Papa.' She pauses, feels the string pull, then says, softer: 'It tugs.' Flat fluorescent light. Sound: a low hum.")
S+=("On the hotel corridor, warm beige walls, a close-up on Moth's face alone, $MOTH. Her shoulders drop and her eyes go unfocused; she exhales slowly, her eyes on Pip just beside the lens, and says, soft and tired, trailing off at the end: 'Every room is the same room. I keep losing the way.' Warm ceiling light. Sound: a carpet hush.")
S+=("On the dark mall escalator, green-lit, a close-up on Sprout's face alone, $SPROUT. She faces the camera and says, in a small voice: 'If the balloon goes up, we go with it, right, Papa?' Low green light. Sound: a low escalator hum.")
{
  print -r -- "NAME=$NAME; SIZE=480p; SECS=8; SEED=411; PORTRAIT=1; MODE=\"\""
  print -r -- "ANCHOR_STRENGTH=0"
  print -r -- "BIBLE='$BIBLE'"
  print -r -- "SCENES=("
  for s in "${S[@]}"; do print -r -- "\"$s\""; done
  print -r -- ")"
} > $P
for i in 1 2 3 4; do
  cp $FIX/scene-$i.mp4 $OUT/scene-$i.mp4
  python3 -c "import json,sys; json.dump({'prompt': sys.argv[1]+' '+sys.argv[2], 'seed': 411, 'mode': 'fast', 'size': '480p', 'seconds': 8.0, 'verb': 'generate'}, open(sys.argv[3],'w'), indent=1)" "${S[$i]}" "$BIBLE" $OUT/scene-$i.json
done
cp $P $OUT/project.txt
echo "$P ready; $OUT has clips 1-4"
