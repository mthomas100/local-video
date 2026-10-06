# Why dialogue drifted out of sync through a film, and the fix (2026-10-03)

**The symptom a viewer reported:** the films started in sync and then drifted off.

**Root cause: the stitch, not the model or the prompts.**
- **Each clip's audio is 58 ms longer than its picture.** Every clip from `vidgen` has 8.100 s of AAC audio over
  8.042 s of video (193 frames at 24 fps).
- **The joins left gaps.** The stitch (`stories/story.sh` up to commit d2c2bf6's parent) re-encoded each clip's
  audio to AAC on its own, then joined the clips with the ffmpeg concat demuxer, re-encoding the video only once.
  That left a gap in the audio timestamps at every join.
  - Warm: 24 audio packets spaced 100.7 ms instead of 10.7 ms, i.e. ~90 ms gaps.
  - Warm: 23 video gaps of 42-83 ms.
- **Apple players ignore the gaps.** QuickTime, iOS and AVFoundation play AAC samples back to back.
  - An AVFoundation export of warm.mp4 lasts 189.25 s; the film lasts 191.41 s.
  - ffmpeg decoding gives 189.25 s back to back and 191.41 s with `aresample=async=1`.
- **Result:** after every cut, the voice plays ~90 ms earlier than the lips.

**Measured with rig/sync/drift.py (new): the voice was early by the end of each film.**

| film | joins | voice early at the end |
|---|---|---|
| warm | 23 | 2160 ms |
| liminal-clowns | 21 | 1980 ms |
| halloween-clowns-sf-portrait | 15 | 1440 ms |
| halloween-clowns-sf | 15 | 1440 ms |

**Lip movement, measured** with the rig's SyncNet meter (`rig/sync/syncmeter.py --verdict`; JSON files in this
folder; positive offset = audio early). Clips were cut from a "player view" of the old film: the picture by its
timestamps, the sound decoded back to back.

| Warm shot | cuts before it | raw clip | old film, player view | fixed stitch |
|---|---|---|---|---|
| 3 | 2 | PASS -12 ms | **FAIL +207 ms** | PASS -12 ms |
| 6 | 5 | PASS -3 ms | **FAIL +470 ms** | PASS -3 ms |
| 7 | 6 | PASS -39 ms | **FAIL +595 ms** (at the meter's search edge) | PASS -39 ms |

**Why the rig said "13/13 in sync".** backmeasure.py cut each shot out of the final film with `-ss`. Seeking
re-anchors audio and video at the window's start, so every window read in sync, and a cumulative drift is
invisible to any per-shot meter.

**The fix (commit d2c2bf6).**
- Each clip's picture is copied unchanged.
- Each clip's sound is decoded to PCM at 48 kHz and cut or padded to exactly its frame count (2000 samples a frame).
- Picture and sound are joined as two exact lists, and the AAC encode happens once.
- drift.py runs after every stitch.

Results:
- Warm re-stitched: 4560 frames = 190.000 s; the AVFoundation export lasts 190.02 s; 0 gaps; 0 ms drift.
- The four films above are re-stitched next to the originals as `~/Videos/vidgen/<film>/<film>-resynced.mp4`, all
  0 gaps and 0 ms drift.
