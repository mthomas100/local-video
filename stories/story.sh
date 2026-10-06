#!/bin/zsh
# story.sh <project-file> — generic multi-scene film runner (2026-09-23). Unattended by default.
# A project file is zsh that sets: NAME SIZE SECS SEED PORTRAIT(0/1) MODE("" or --quality)
# BIBLE (shared character/setting paragraph) and SCENES=( "..." "..." ). Scene text may start
# with tokens: [noanchor] (fresh start, e.g. a location jump) [ref=N] (anchor to scene N instead
# of the previous one) [secs=N] (override length) [pair] (anchor needs two faces) [seed=N] (this
# scene only; same text + same seed reproduces the same clip, so a redo needs one or the other changed)
# [quality] / [fast] (2026-09-24: this scene in vidgen --quality, dev model with guidance, or in fast
# mode, whatever MODE says; spend the slow mode on the landmark and hero shots only).
# [still] (2026-09-26): keyframe-first. bin/still draws the shot's first frame with Qwen-Image-2.1 from the line
# itself (dialogue left out), at the video's frame size, and vidgen animates it (-i, frame 0). The image model holds
# a landmark's real shape and a character's look far better than the video model's text alone
# (rig/bench/char-keyframe.py). The still is redrawn when the line, the bible or the seed changes (still-N.key);
# redo.sh moves it into redo-N/ with its take.
#
# Continuity, and why it is not "pin frame 0": the 2026-09-22 run pinned every scene's first
# frame to the same reference at strength 0.85, so every scene opened on the same shot. Now the
# reference (best face frame of the PREVIOUS scene, macOS Vision via bin/pick-face-frame) is
# placed at latent-friendly pixel frame ANCHOR_FRAME (default 16) at ANCHOR_STRENGTH (default
# 0.6): a guide the clip passes through, not an opening still. Both are per-project overrides.
# LTX-2.5 also cuts within a scene when the text says "cut to", so scenes can hold 2-3 shots.
#
# [place=stories/refs/x.png] (2026-09-27): the shot opens on a reference photo of the place (the human's own images):
# bin/still --place centre-crops it to the frame and redraws it crisply (Qwen image-to-image, strength 0.7, which keeps the
# room and adds no people), and vidgen animates it; the line says who walks in and what happens. Measured on the human's
# hotel-corridor photo: the corridor held exactly, and a family of four clowns walked in from the far end.
# [cast=a,b] (2026-09-27): the shot's first frame is drawn by FLUX.2 klein 4B from references: the place photo first (if
# [place] is also given), then the portraits of characters a and b. Portraits come from the project's
# CAST=( "a|<one-sentence look>" ... ), drawn once per film as $OUT/cast-a.png (bin/still --portrait) and reused by
# every shot, so each character keeps one face; on 2026-09-26 independent stills gave Marrow about five faces.
# [layout] (2026-10-03, shot lab): with [cast] and no [place], first draw the shot's composition from the line
# (text mode, same seed) and use it as image 1: without it the first portrait is image 1 and its layout is kept, so
# the cast always comes out at the portrait's scale ("full length" and "wide" lines drew waist-up).
# [hold] (2026-10-04, shot lab): the shot's own still again near the end of the clip (engine --image at frame
# secs*24-8, HOLD_STRENGTH default 0.7), so a speaker drawn small stays small instead of walking to the lens.
# SOUND="..." (2026-09-27): the film's sound sentence, appended to every video prompt as "Sound: ..." and never given
# to the image model, which drew the bible's "a saxophone" in four shots on 2026-09-26. Keep sound nouns out of BIBLE.
# ONLY="3 7" (set by redo.sh, 2026-09-24): render only those scenes, and stitch only when every scene
# exists. Before, redo on a paused film reran the whole runner and rendered every missing scene (scenes
# 3 to 12, 26 min with no review stop, when one retake was asked for).
# The stitch (2026-09-24) gives each clip's audio a 40 ms fade in and an 80 ms fade out, so the cuts of a
# one-shot-per-clip film do not click; since 2026-10-03 each clip's sound is cut to its exact frame count (see the stitch).
set -u
proj=$1; [ -f $proj ] || { echo "no project $proj"; exit 2; }
ONLY=${ONLY:-}
SIZE=720p; SECS=15; SEED=7; PORTRAIT=0; MODE=""; ANCHOR_FRAME=16; ANCHOR_STRENGTH=0.6; SOUND=""; typeset -a CAST; CAST=()
source $proj
OUT=~/Videos/vidgen/$NAME; mkdir -p $OUT; LOG=~/repos/local-video/logs/story-$NAME.log
# the prompts travel with the video; bin/catalog reads this. CAST=( "..." ) entries are indented in the copy (2026-09-27)
# so tools that take every line starting with a double quote as a scene (older pi sessions, awk counts) skip them.
awk '/^CAST=\(/{c=1; print; next} c && /^\)/{c=0} c && /^"/{print "  " $0; next} {print}' $proj > $OUT/project.txt
[ "$PORTRAIT" = 1 ] && PFLAG=--portrait || PFLAG=""
echo "=== $NAME: ${#SCENES[@]} scenes, $SIZE, ${SECS}s, seed $SEED $(date)" | tee -a $LOG
REPO=~/repos/local-video
# One GPU lock for the Mac (2026-10-04, ~/repos/local-rig/docs/hold.md), taken at the first GPU step rather than at the
# start: keep_take re-stitches through this script with nothing to render and must not unload the director's model.
# Kept until the script exits (the gate ends a hold whose process is gone), so no model call reloads the LLM between
# scenes. Under run-queue.sh, redo.sh or render_and_wait it is already held (HOLD_ID); bin/still and vidgen run inside.
gpu_hold() {
  [ -n "${HOLD_ID:-}" ] && return 0
  if command -v hold >/dev/null; then HOLD_ID=$(hold acquire --pid $$ --kind render --reason "$NAME" 2>>$LOG) || HOLD_ID=none; else HOLD_ID=none; fi
  export HOLD_ID
}
# cast portraits, once per film (redrawn when a character's sentence changes); only when some line uses [cast=]
if (( ${#CAST} )) && print -r -- "${SCENES[*]}" | grep -q '\[cast='; then
  for c in "${CAST[@]}"; do
    cn=${c%%|*}; cs=${c#*|}; ck=$(print -r -- "$cs $SEED" | shasum | cut -c1-16)
    if [ ! -s $OUT/cast-$cn.png ] || [ "$(cat $OUT/cast-$cn.key 2>/dev/null)" != "$ck" ]; then
      echo "--- cast portrait $cn $(date +%H:%M)" | tee -a $LOG
      gpu_hold
      $REPO/bin/still --portrait -o $OUT/cast-$cn.png --size 768x1152 --seed $SEED "$cs" >> $LOG 2>&1 \
        || { echo "cast portrait $cn FAILED (see $LOG)" | tee -a $LOG; exit 1; }
      print -r -- $ck > $OUT/cast-$cn.key
    fi
  done
fi
i=0
for s in "${SCENES[@]}"; do
  i=$((i+1)); f=$OUT/scene-$i.mp4
  secs=$SECS; anchor=1; refn=$((i-1)); want=1; seed=$SEED; smode=$MODE; still=0; place=""; cast=""; layout=0; hold=0
  while [[ $s == \[*\]* ]]; do
    tok=${s%%\]*}; tok=${tok#\[}; s=${s#*\] }
    case $tok in noanchor) anchor=0;; ref=*) refn=${tok#ref=};; secs=*) secs=${tok#secs=};; pair) want=2;; seed=*) seed=${tok#seed=};; quality) smode=--quality;; fast) smode="";; still) still=1;; place=*) place=${tok#place=};; cast=*) cast=${tok#cast=};; layout) layout=1;; hold) hold=1;; esac
  done
  if [ -n "$ONLY" ] && [[ " $ONLY " != *" $i "* ]]; then continue; fi
  if [ -s $f ]; then echo "scene $i exists, skipping" | tee -a $LOG; continue; fi
  # stop-after (2026-09-23, rig): a file $OUT/stop-after holding a scene number makes the run stop
  # cleanly BEFORE starting the next scene, so a review at scene 3 wastes no partial render; exit 3
  # so run-queue.sh logs PAUSED, not FAILED. Delete the file and rerun to continue (done scenes skip).
  if [ -s $OUT/stop-after ] && [ $i -gt $(cat $OUT/stop-after) ]; then
    echo "PAUSED $NAME before scene $i (stop-after $(cat $OUT/stop-after)) $(date)" | tee -a $LOG; exit 3
  fi
  typeset -a ref; ref=()
  # ANCHOR_STRENGTH=0 disables anchoring for the whole project (2026-09-23 03:00): with the bible
  # after the scene and each character described in-scene, a fixed seed held identity across ten
  # unanchored scenes, while a 0.6 anchor on an extreme-close-up reference froze the next scene on
  # that same shot for 15 s (vasilisa scenes 5-6). Faces picked by "largest face" are usually
  # extreme close-ups, so this bites often.
  [ "$ANCHOR_STRENGTH" = 0 ] && anchor=0
  if [ $i -gt 1 ] && [ $anchor = 1 ] && [ -s $OUT/scene-$refn.mp4 ]; then
    png=$OUT/ref-from-$refn.png
    [ -s $png ] || ~/repos/local-video/bin/pick-face-frame $OUT/scene-$refn.mp4 $png $want 2>&1 | tee -a $LOG
    [ -s $png ] && ref=(-- --image $png $ANCHOR_FRAME $ANCHOR_STRENGTH)
  fi
  typeset -a first; first=()
  if [ $still = 1 ] || [ -n "$place" ] || [ -n "$cast" ]; then
    case $SIZE in 480p) wh=704x448;; 720p) wh=1280x704;; 1080p) wh=1920x1088;; *) wh=$SIZE;; esac
    [ "$PORTRAIT" = 1 ] && wh=${wh#*x}x${wh%x*}
    stillpng=$OUT/still-$i.png
    typeset -a sargs; sargs=()
    [ -n "$place" ] && [[ $place != /* ]] && place=$REPO/$place
    if [ -n "$cast" ]; then
      [ -n "$place" ] && sargs+=(--ref $place)
      # [layout] (2026-10-03, shot lab): with no [place], the first cast portrait would be image 1 and its layout kept,
      # so the cast always comes out at the portrait's scale ("full length" and "wide" lines drew waist-up). Draw the
      # shot's composition from the line first and pass it as image 1 (the place); the portraits give the faces.
      if [ -z "$place" ] && [ $layout = 1 ]; then
        lay=$OUT/layout-$i.png; lkey=$(print -r -- "$seed $wh $s $BIBLE layout" | shasum | cut -c1-16)
        if [ ! -s $lay ] || [ "$(cat $OUT/layout-$i.key 2>/dev/null)" != "$lkey" ]; then
          echo "--- scene $i layout $(date +%H:%M) $wh seed $seed" | tee -a $LOG
          gpu_hold
          $REPO/bin/still -o $lay --size $wh --seed $seed "$s $BIBLE" >> $LOG 2>&1 \
            || { echo "scene $i layout FAILED (see $LOG)" | tee -a $LOG; exit 1; }
          print -r -- $lkey > $OUT/layout-$i.key
        fi
        sargs+=(--ref $lay)
      fi
      for cn in ${(s:,:)cast}; do [ -s $OUT/cast-$cn.png ] || { echo "scene $i: no cast portrait $cn (add it to CAST)" | tee -a $LOG; exit 1; }; sargs+=(--ref $OUT/cast-$cn.png); done
    elif [ -n "$place" ]; then
      [ -s $place ] || { echo "scene $i: no place image $place" | tee -a $LOG; exit 1; }
      sargs=(--place $place)
    fi
    if (( ${#sargs} )); then key=$(print -r -- "$seed $wh $s $BIBLE ${sargs[*]} $(cat ${sargs[@]:#--*} /dev/null 2>/dev/null | shasum | cut -c1-8)" | shasum | cut -c1-16)
    else key=$(print -r -- "$seed $wh $s $BIBLE" | shasum | cut -c1-16); fi
    if [ ! -s $stillpng ] || [ "$(cat $OUT/still-$i.key 2>/dev/null)" != "$key" ]; then
      echo "--- scene $i still $(date +%H:%M) $wh seed $seed ${sargs[*]}" | tee -a $LOG
      gpu_hold
      $REPO/bin/still -o $stillpng --size $wh --seed $seed "${sargs[@]}" "$s $BIBLE" >> $LOG 2>&1 \
        || { echo "scene $i still FAILED (see $LOG)" | tee -a $LOG; exit 1; }
      print -r -- $key > $OUT/still-$i.key
    fi
    first=(-i $stillpng)
    # [hold] (2026-10-04, shot lab): the shot's own first frame again near the end, so the speaker stays where the still
    # put them (wide stills drew Dana tiny far down the street; in the video she walked to the lens to speak)
    if [ $hold = 1 ]; then
      (( ${#ref} )) || ref=(--)
      ref+=(--image $stillpng $(( secs * 24 - 8 )) ${HOLD_STRENGTH:-0.7})
    fi
  fi
  echo "--- scene $i/${#SCENES[@]} $(date +%H:%M) anchor=${ref[4]:-none} mode=${smode:-fast}${first:+ still=still-$i.png}" | tee -a $LOG
  # Bible AFTER the scene (2026-09-23 02:20): three drafts showed LTX-2.5 stages whatever the prompt
  # opens with as its first shot. Leading with the bible gave every scene a 2-6 s prologue of the
  # bible's content (both leads posing; a crowd; the Firebird) before the scene began. Trailing
  # style text, as in the human's fashion prompts, does not get staged.
  # The dialogue-sync gate (2026-09-27, iteration 5; rig/sync/gate.py, `docs/dialogue-sync.md`): a clip whose line
  # has a spoken line is measured on the CPU right after it renders (rig/sync/syncmeter.py: SyncNet offset and
  # confidence on the speaker's face against the separated voice). Not PASS: the take moves to takes/ and the shot is
  # re-rendered with another VIDEO seed (same first frame), up to SYNC_TRIES takes in all; the best take stays.
  # Measured 2026-09-27: the same line and still at another seed changes the offset and articulation (phase-2 A/B).
  tries=${SYNC_TRIES:-3}; t=1; vseed=$seed
  while :; do
    gpu_hold
    vidgen --no-open $smode $PFLAG --seconds $secs --size $SIZE --seed $vseed -o $f "${first[@]}" "$s $BIBLE${SOUND:+ Sound: $SOUND}" "${ref[@]}" >> $LOG 2>&1 \
      || { echo "scene $i FAILED (see $LOG)" | tee -a $LOG; exit 1; }
    # a retake's sidecar keeps the line's own seed, so the director's tools still see this clip as the line's take
    [ $vseed != $seed ] && python3 -c "import json,sys; p=sys.argv[1]; j=json.load(open(p)); j['line_seed']=int(sys.argv[2]); j['sync_retake']=int(sys.argv[3]); json.dump(j,open(p,'w'),indent=1)" ${f%.mp4}.json $seed $t
    [ "${SYNC_GATE:-enforce}" = off ] && break
    g=$(python3 $REPO/rig/sync/gate.py $NAME $i 2>>$LOG | tail -1)
    [ -z "$g" ] && break                                   # no spoken line in this scene
    echo "$g" | tee -a $LOG
    [[ $g == *": PASS"* || $g == *OFFSCREEN* ]] && break
    if (( t >= tries )); then python3 $REPO/rig/sync/gate.py best $NAME $i 2>>$LOG | tee -a $LOG; break; fi
    mkdir -p $OUT/takes
    mv $f $OUT/takes/scene-$i-try$t.mp4; mv ${f%.mp4}.json $OUT/takes/scene-$i-try$t.json; mv $OUT/sync-$i.json $OUT/takes/sync-$i-try$t.json
    t=$((t+1)); vseed=$((seed + 7919 * (t - 1)))
    echo "--- scene $i sync retake $t/$tries (video seed $vseed, same first frame) $(date +%H:%M)" | tee -a $LOG
  done
done
missing=(); for j in {1..${#SCENES[@]}}; do [ -s $OUT/scene-$j.mp4 ] || missing+=($j); done
if (( ${#missing} )); then echo "NOT STITCHED $NAME: scenes missing: ${missing[*]} $(date)" | tee -a $LOG; exit 0; fi
# The stitch refuses a dialogue shot that is not in sync (2026-09-27): FAIL or UNMEASURABLE blocks unless the director
# recorded an exception for that take (keep_take accept_sync_fail). SYNC_GATE=report stitches anyway; exit 4 = blocked.
if [ "${SYNC_GATE:-enforce}" != off ]; then
  gate_out=$(python3 $REPO/rig/sync/gate.py stitch-check $NAME ${#SCENES[@]} 2>>$LOG); gate_rc=$?   # not through tee: its status would hide the gate's
  [ -n "$gate_out" ] && print -r -- "$gate_out" | tee -a $LOG
  if [ $gate_rc != 0 ]; then echo "NOT STITCHED $NAME: the sync gate refused the shots above $(date)" | tee -a $LOG; exit 4; fi
fi
EDIT=$OUT/.edit; rm -rf $EDIT; mkdir -p $EDIT; : > $OUT/list.txt; : > $EDIT/alist.txt; : > $OUT/lipsync-nudges.txt
# The stitch keeps sound and picture on one clock (2026-10-03, iteration 6). Each clip's audio was 58 ms longer than its
# video (8.100 vs 8.042 s) and was re-encoded to AAC per clip, then joined with the concat demuxer: every join left a
# ~90 ms gap in the audio timestamps. QuickTime, iOS and AVFoundation play AAC samples back to back and ignore such
# gaps, so the voice ran ~90 ms earlier after every cut: 1.4-2.2 s early by the end of the last four films
# (rig/sync/drift.py), while per-shot meters, which seek to each shot, read them in sync. Now each clip's picture is
# copied as is and its sound is decoded to PCM at 48 kHz and cut or padded to exactly its frame count (2000 samples a
# frame at 24 fps); picture and sound are joined as two exact lists and the sound is encoded to AAC once.
for j in {1..${#SCENES[@]}}; do
  nf=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 $OUT/scene-$j.mp4)
  fr=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 $OUT/scene-$j.mp4)
  ns=$(python3 -c "from fractions import Fraction as F; print(round($nf*48000/F('$fr')))")
  d=$(python3 -c "print($ns/48000)")
  # lip-sync nudge (2026-09-27, rig/audit/lipsync.py nudge): a dialogue clip whose mouth clearly matches its voice at
  # an offset gets its audio shifted by that offset in the stitched film; the rendered clip is not changed.
  line=${SCENES[$j]}; while [[ $line == \[*\]* ]]; do line=${line#*\] }; done
  # OFF by default since 2026-09-27 12:40: the human found many liminal-clowns dialogue shots out of sync while this
  # meter passed 9 of 10, and its pass rule calls a planted 400 ms offset "in sync" (`docs/dialogue-sync.md`).
  # A shift from an uncalibrated meter can make sync worse; LIPSYNC_NUDGE=1 re-enables it until the calibrated gate lands.
  nudge=0
  [ "${LIPSYNC_NUDGE:-0}" = 1 ] && nudge=$(python3 $REPO/rig/audit/lipsync.py nudge $OUT/scene-$j.mp4 "$line" 2>/dev/null || echo 0)
  shift=""
  if [[ $nudge == -* ]] && [ $nudge != 0 ]; then shift="atrim=start=$(( -nudge / 1000.0 )),asetpts=PTS-STARTPTS,"
  elif [ "${nudge:-0}" -gt 0 ] 2>/dev/null; then shift="adelay=${nudge}:all=1,"; fi
  [ -n "$shift" ] && echo "scene $j: audio shifted ${nudge} ms (the mouth matched the voice at that offset)" | tee -a $LOG >> $OUT/lipsync-nudges.txt
  ffmpeg -hide_banner -loglevel error -y -i $OUT/scene-$j.mp4 -an -c:v copy $EDIT/v-$j.mp4 2>>$LOG
  echo "file '$EDIT/v-$j.mp4'" >> $OUT/list.txt
  if ! ffmpeg -hide_banner -loglevel error -y -i $OUT/scene-$j.mp4 -vn \
       -af "${shift}aresample=48000,aformat=channel_layouts=stereo,apad=whole_len=$ns,atrim=end_sample=$ns,afade=t=in:d=0.04,afade=t=out:st=$(( d - 0.08 )):d=0.08" \
       -c:a pcm_s16le $EDIT/a-$j.wav 2>>$LOG; then
    # no audio track: silence of the clip's exact length
    ffmpeg -hide_banner -loglevel error -y -f lavfi -i anullsrc=r=48000:cl=stereo -af "atrim=end_sample=$ns" -c:a pcm_s16le $EDIT/a-$j.wav 2>>$LOG
  fi
  echo "file '$EDIT/a-$j.wav'" >> $EDIT/alist.txt
done
fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 $OUT/scene-1.mp4)
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $OUT/list.txt -f concat -safe 0 -i $EDIT/alist.txt \
  -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -fps_mode cfr -r $fps -c:a aac -b:a 192k -movflags +faststart $OUT/$NAME.mp4 \
  && echo "DONE $NAME → $OUT/$NAME.mp4 $(date)" | tee -a $LOG
# Film-level drift check (2026-10-03): what a player that plays the sound back to back hears at every cut.
python3 $REPO/rig/sync/drift.py $OUT/$NAME.mp4 2>>$LOG | head -1 | tee -a $LOG
[ "${SYNC_GATE:-enforce}" != off ] && python3 $REPO/rig/sync/gate.py report $NAME ${#SCENES[@]} 2>>$LOG | head -1 | tee -a $LOG
rm -rf $EDIT
~/repos/local-video/bin/catalog >/dev/null 2>&1 || true
