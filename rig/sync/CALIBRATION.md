# Calibration of the dialogue-sync meter (rig/sync/syncmeter.py, meter v2) — 2026-09-27, iteration 5

Machine ground truth only (a design rule: no human labelling). Raw rows: `docs/data/sync-calibration/`.
Re-run any table: `~/.cache/local-video/sync-venv/bin/python rig/sync/controls_table.py <rows.jsonl> --reverdict`,
`rig/sync/baseline.py <backmeasure rows>`. Sign: offset + = audio early (the voice before the mouth).

## Instruments (all local, CPU)
Demucs htdemucs (the voice apart from ambience), S3FD face boxes every 2nd frame, SyncNet v2 on 224-px face crops
(audio re-timed to 25 fps; sub-frame parabolic offset), MediaPipe lips on the crops, torchaudio MMS_FA forced alignment
of the asked words, p/b/m lip closure vs a random baseline. 8-30 s per 8 s clip (the §4.3 bar is 60 s).
Face detectors on painted clowns (liminal-clowns shot 7, a frontal close-up): MediaPipe 13% of frames, macOS Vision
31%, **S3FD 100%**. Shot 16's SyncNet confidence rose from about 3 (MediaPipe crops) to 8 (S3FD crops).

## 1. Planted controls on our own footage (truth by construction; rig/sync/make_controls.py)
Sources: liminal-clowns shots 3 (Moth close-up), 16 (Pip close-up), 11 (Sprout close-up), 6 (Sprout medium, face
0.12 of frame height), 2 (Pip medium at a door, face 0.12). Shifts -400..+400 ms, a different-words swap, the face
covered, the first frame frozen under the voice.

- **55/55 planted shifts recovered within 10 ms** (bar: one frame, 42 ms).
- Swaps 5/5 FAIL (conf 1.2-3.74). Hidden 5/5 UNMEASURABLE. Frozen 4/5 FAIL + 1 UNMEASURABLE (conf 0.8-3.2; src2 4.6
  with the face under the coverage bar). Nothing that should fail passes.
- Detection by |planted| with the window +45 / -125 ms: 40 ms 0/10 flagged (inside the window by design), 80 ms 4/10
  (the audio-early side), 120 ms 10/10, 200 ms 10/10, 400 ms 10/10.

## 2. Real talking faces in sync by construction (RAVDESS, actors 1-2; research use, local, not in git)
Neutral, angry-strong and sad-strong takes of the same sentences, shifts -200..+200 ms, swaps, hidden, frozen.
- **54/54 planted shifts within 8 ms.** Frozen 6/6 FAIL (conf 1.23-3.7). Hidden 6/6 UNMEASURABLE.
- Swaps: 4/6 FAIL; the 2 that pass (conf 4.48, 6.17) swapped in **the same sentence** spoken by another actor with
  nearly the same timing, a plausible dub. Different-words swaps never pass (on either footage).
- In-sync takes read **-67 to -81 ms** at conf 4.66-10.03. The lowest confidence is the strong *sad* take: quiet
  speech moves the mouth less.

**Confidence bar = 4.2**: above every frozen mouth and every different-words swap (max 3.74), below every real in-sync
take (min 4.66). Coverage bar 0.5 (liminal shot 2's face is visible in 59% of its speech and it measures at conf
9.2, the same offset as its raw clip). Words bar 0.6 (a swapped voice aligned 3/11 words). A best offset at the +-15
frame search edge = no sync peak (FAIL).

## 3. The absolute zero point
Relative offsets are exact to about 10 ms. The absolute zero was open until 15:25: truly in-sync RAVDESS reads about
-72 ms (1-2 frames audio-late), LTX raw clips read -15 to -61 ms (median -41). Either SyncNet's convention on this
pipeline reads about 70 ms late, or RAVDESS's recording has that lag.

**Settled (2026-09-27 15:25): the meter's zero is SyncNet's zero; the lag is in RAVDESS.**
The reference implementation (joonson/syncnet_python README) publishes its demo clip `data/example.avi` (25 fps, PCM
16 kHz) as "AV offset: 3" frames = +120 ms (audio early), confidence 10.021. This meter reads the same clip:

| the reference clip, through | offset | conf |
|---|---|---|
| as published (25 fps, PCM) | **+123 ms** (+124 on a rerun) | 10.64 |
| 25 fps, AAC 48 kHz in mp4 (the codec path) | +123 ms | 10.61 |
| re-timed to 24 fps (`fps=24`; the LTX path: audio re-timed 24→25) | +125 ms | 10.31 |
| re-timed to 29.97 fps (the RAVDESS path) | +130 ms | 7.14 |

So the pipeline adds at most 2-10 ms on every path we use, and a reading is an offset against SyncNet's convention
(the literature's standard; SyncNet was trained on broadcast footage taken as in sync). RAVDESS's -72 ms is in the
RAVDESS recordings (both of its streams start at 0 s; no container offset). LTX joint clips (median -41 ms) are
slightly audio-late, inside BT.1359 detectability (125 ms late). The window stays +45 / -125 ms around 0. The
hypothesis that a biased zero hides audio-early shots in liminal-clowns (shots 2 and 7 read +13 and +4 ms in the
final cut) is ruled out; the viewer's report that many lines looked out of sync is still open (§4). Rows: `sync-cal/zero-reference.jsonl`.

## 4. Back-measure (rig/sync/backmeasure.py; the baseline for the next film)

### liminal-clowns (meter v2)

| shot | line | final cut | raw clip | final - raw (ms) | earlier takes |
|---|---|---|---|---|---|
| 2 | This door again. We've walked past it twice. It  | PASS +13 ms, conf 9.16 | PASS -16 ms, conf 8.79 | +29 | redo-2: **UNMEASURABLE** -39 ms, conf 9.33 (speaker not visible) |
| 3 | We have to keep walking, Pip. The light's still  | PASS -37 ms, conf 9.33 | PASS -23 ms, conf 9.07 | -14 | redo-2: PASS -63 ms, conf 8.39 |
| 6 | The water's so still. Is it a pool or a floor? I | PASS -25 ms, conf 6.79 | PASS -15 ms, conf 7.0 | -10 |  |
| 7 | Don't look too long. The reflection looks back a | PASS +4 ms, conf 8.73 | PASS -27 ms, conf 8.52 | +31 |  |
| 10 | Every room is the same room. I keep losing the w | **FAIL** +323 ms, conf 9.18 (offset) | PASS -41 ms, conf 9.25 | +364 | redo-4: PASS -44 ms, conf 8.79; redo-5: PASS -58 ms, conf 8.8 |
| 11 | But the balloon always knows the way home, Papa. | PASS -55 ms, conf 8.31 | PASS -44 ms, conf 8.79 | -11 |  |
| 15 | This is the one. This light is the way through.  | PASS -63 ms, conf 6.03 | PASS -52 ms, conf 6.26 | -11 |  |
| 16 | We follow the light. It never goes dark, not onc | PASS -58 ms, conf 7.41 | PASS -46 ms, conf 8.13 | -12 |  |
| 19 | This is the last one. We ride up into the light, | PASS -57 ms, conf 8.49 | PASS -47 ms, conf 8.82 | -10 |  |
| 20 | If the balloon goes up, we go with it, right, Pa | PASS -54 ms, conf 7.53 | PASS -46 ms, conf 8.37 | -8 |  |

Final cut: 9/10 dialogue shots PASS. Raw clip offsets (conf >= 5): median -41 ms, range -52..-15. Final minus raw: +29, -14, -10, +31, +364, -11, -11, -12, -10, -8 ms.

### halloween-clowns-sf (meter v2)

| shot | line | final cut | raw clip | final - raw (ms) | earlier takes |
|---|---|---|---|---|---|
| 5 | The streets are ours. | PASS -75 ms, conf 8.14 | PASS -61 ms, conf 7.72 | -14 |  |
| 6 | Come out, come out. | **FAIL** -127 ms, conf 10.36 (offset) | PASS -120 ms, conf 9.55 | -7 |  |
| 8 | I hear you. | **FAIL** -90 ms, conf 2.81 (mouth does not follow / no sync peak) | **FAIL** -82 ms, conf 3.15 (mouth does not follow / no sync peak) | -8 |  |
| 9 | Why is everything webbed? | PASS -89 ms, conf 6.91 | PASS -81 ms, conf 7.74 | -8 |  |
| 11 | No, no. | **UNMEASURABLE** -143 ms, conf 1.48 (speaker not visible) | **UNMEASURABLE** -130 ms, conf 1.58 (speaker not visible) | -13 |  |
| 12 | They're everywhere. | **UNMEASURABLE** +625 ms, conf 5.12 (speaker not visible) | **UNMEASURABLE** +569 ms, conf 5.37 (speaker not visible) | +56 | redo-1: **UNMEASURABLE** -625 ms, conf 2.85 (speaker not visible) |
| 13 | The streets are ours. | **FAIL** -94 ms, conf 3.18 (mouth does not follow / no sync peak) | **FAIL** -86 ms, conf 3.26 (mouth does not follow / no sync peak) | -8 |  |
| 16 | Happy Halloween. | PASS -74 ms, conf 8.12 | PASS -56 ms, conf 8.47 | -18 |  |

Final cut: 3/8 dialogue shots PASS. Raw clip offsets (conf >= 5): median -61 ms, range -120..569. Final minus raw: -14, -7, -8, -8, -13, +56, -8, -18 ms.

### halloween-clowns-sf-portrait (meter v2)

| shot | line | final cut | raw clip | final - raw (ms) | earlier takes |
|---|---|---|---|---|---|
| 5 | The streets are ours. | PASS -54 ms, conf 8.73 | PASS -44 ms, conf 8.23 | -10 |  |
| 6 | Come out, come out. | **FAIL** -41 ms, conf 10.81 (line not spoken) | **FAIL** -30 ms, conf 10.25 (line not spoken) | -11 | redo-1: **FAIL** -625 ms, conf 3.65 (mouth does not follow / no sync peak) |
| 8 | I hear you. | **FAIL** +0 ms, conf 2.94 (mouth does not follow / no sync peak) | **FAIL** +8 ms, conf 2.87 (mouth does not follow / no sync peak) | -8 | redo-1: **FAIL** +2 ms, conf 1.48 (mouth does not follow / no sync peak) |
| 9 | Why is everything webbed? | PASS -47 ms, conf 6.44 | PASS -38 ms, conf 9.97 | -9 |  |
| 11 | No, no. | **UNMEASURABLE** +625 ms, conf 1.27 (speaker not visible) | **UNMEASURABLE** +625 ms, conf 0.81 (speaker not visible) | +0 |  |
| 12 | They're everywhere. | **UNMEASURABLE** -625 ms, conf 5.33 (speaker not visible) | **UNMEASURABLE** -625 ms, conf 5.0 (speaker not visible) | +0 |  |
| 13 | The streets are ours. | **FAIL** -69 ms, conf 3.07 (mouth does not follow / no sync peak) | **FAIL** -55 ms, conf 2.98 (mouth does not follow / no sync peak) | -14 | redo-1: PASS -55 ms, conf 8.73 |
| 16 | Happy Halloween. | PASS -34 ms, conf 6.88 | PASS -24 ms, conf 6.33 | -10 |  |

Final cut: 3/8 dialogue shots PASS. Raw clip offsets (conf >= 5): median -38 ms, range -625..-24. Final minus raw: -10, -11, -8, -9, +0, +0, -14, -10 ms.

**Readings.**
- **P1 confirmed, one shot:** liminal-clowns shot 10 is in sync as rendered (-41 ms, conf 9.25) and **+323 ms audio
  early** in the final film: the stitch "nudge" (from the uncalibrated old meter) shifted it by -375 ms. The nudge is
  off by default since 2026-09-27 12:40.
- **The stitch itself** adds a steady -8 to -14 ms (audio a little later; AAC re-encode), no drift along a 3-minute
  film (P2: no trend with position).
- **Model failures are real in the halloween films:** mouths that do not follow the voice (conf 2.8-3.3: sf 8, 13;
  portrait 8, 13), a line never spoken (portrait 6: 0/4 words), speakers not visible (11, 12 in both). One earlier
  take of portrait 13 passes at conf 8.7: a new seed fixes M3 cases.
- **liminal-clowns: 9/10 by this meter**, the same count the old meter reported but a different set: the old meter
  failed shot 11 (in sync here) and passed shot 10 (the nudged one). A viewer reported that many were out of sync. The
  remaining disagreement is checked by independent instruments (the local judge, §5) and by the delivery meter,
  since a flat, mismatched voice can read as "out of sync".

## 5. The old meter on the same controls (for the record)
rig/audit/lipsync.py passed a 400 ms offset in both directions (`docs/dialogue-sync.md`).

## 6. The delivery meter (rig/sync/delivery.py) on known answers: RAVDESS actors 1-4
16 neutral takes vs 32 strong-emotion takes (happy, sad, angry, fearful), the same two sentences. Medians:

| | pitch SD (st) | pitch range (st) | loudness SD (dB) | arousal | valence | face motion | brow SD | words/s |
|---|---|---|---|---|---|---|---|---|
| neutral | 3.70 | 9.01 | 6.40 | 0.544 | 0.434 | 0.125 | 0.074 | 4.41 |
| happy | 3.86 | 8.53 | 6.18 | 0.730 | 0.407 | 0.144 | 0.115 | 3.72 |
| sad | 3.52 | 9.00 | 6.15 | 0.661 | 0.399 | 0.114 | 0.085 | 3.67 |
| angry | 4.23 | 8.89 | 6.61 | 0.914 | 0.266 | 0.142 | 0.093 | 3.24 |
| fearful | 3.21 | 6.61 | 6.05 | 0.782 | 0.383 | 0.135 | 0.067 | 4.14 |

Separation emotional > neutral (AUC): **arousal 0.92** (neutral band 0.41-0.60), face motion 0.68, brow SD 0.47,
pitch SD 0.42, pitch range 0.41, loudness SD 0.45; words/s 0.13 (emotional takes are slower).
**Trusted:** arousal ("flat" = inside the neutral band, below 0.60), and words/s as a pace number. **Reported but not
a verdict:** pitch SD/range (on 1-2 s sentences neutral actors still inflect; it did not separate), face motion (weak).

## 7. The local multimodal judge (rig/sync/judge.py, Qwen3-Omni-30B-A3B-Instruct 8-bit, mlx-vlm 0.7.3): no sync vote
A CPU dry run of its input path (processor only, 2026-09-27 15:08) on the src3 control, before any
GPU time: the model gets the clip as 8 temporal groups of 2 frames (16 frames, 2 fps, 2800 tokens) and the voice as a
separate 103-token block after the picture. With `use_audio_in_video=True` the processor emits **no audio tokens** (the
voice is dropped). mlx-vlm's `get_rope_index` for this model is the Qwen2-VL one: audio tokens get sequential text
positions and video frames grid indices, not seconds (no TMRoPE time). So picture and voice share no clock, and at
2 fps no single syllable is seen. It cannot tell a +200 ms shift from sync by construction; it gets no sync vote in
this port. It may still rate delivery from the voice (§6b of the brief); that smoke test (RAVDESS neutral vs strong)
runs after the film, when the GPU is free. A sync-capable local judge needs a TMRoPE implementation and frames at
>= 12 fps on a mouth crop.

**GPU smoke test (2026-09-28 00:09; GPU idle, llama-swap unloaded; 1.5-6.2 s per clip).**
- Sync, src3 controls (shift0, +200 ms, -200 ms, a swapped voice): all four read `"voice early"` at confidence 5.
  So it has no sync discrimination, as the dry run predicted. It is still no sync vote.
- RAVDESS actor 1 (neutral x2, strong angry, strong fearful): `emotion_heard` neutral, neutral, angry, panicked,
  so 4/4 plausible labels.
- The delivery score is 5, 5, 5, 5 and `delivery_tag` is right, right, overacted, right: no separation between flat
  and strong takes. It is not a delivery meter. The arousal meter (§6, AUC 0.92) stays the delivery KPI.
- The judge's emotion label is at most a descriptive note. 4 clips is too few to calibrate it.

## 8. Silent articulation (rig/sync/mouthing.py; reported, not in the gate)
Question: does the speaker's mouth talk where there is no voice (a viewer reads that as out of sync even when the
voiced part is in sync)? Seconds of lip movement outside the voice (150 ms margins; a lip opening held still, e.g. a
smile after the line, does not count). Rows: `docs/data/sync-calibration/mouthing.jsonl`.

| footage | silent articulation (s) |
|---|---|
| real in-sync RAVDESS (12 takes, actors 1-3) | 0.20-0.53 |
| every clip the gate passes: liminal-clowns (10), both halloween films, the phase-2 A/B | 0.00-0.75 (max: liminal shot 6) |
| planted: 1.5 or 2.5 s of a line muted under the moving mouth (liminal 3, 11, 16, 20) | 0.83-2.29 |
| clips the gate already fails (conf < 4.2 or no sync peak) | 0.96-5.42 |

A first version that also counted a still, open mouth flagged halloween-sf shots 6 and 9 (4.6 and 5.3 s "busy");
their lips are parted and still, not talking (0.12 and 0.58 s of movement). So far the gate's confidence bar already
fails every clip that talks without its voice; adding a bar (about 1 s) would change no verdict on any footage we
have, so meter v2 stays as it is and this is reported per shot as a KPI. liminal-clowns reads 0.00-0.08 s on 9 of 10
shots: silent talking does not explain the viewer's report either.

## 9. Small faces and a second mouth (meter v3, 2026-10-03)
**Why.** Meter v2 called a speaker whose face was under 10% of the frame height UNMEASURABLE. That threshold was
never tested below 12%, and the gate turned it into a framing rule: every refused wide shot was rewritten as a
close-up.
- Re-measured with the floor removed, 8 of Warm's 9 UNMEASURABLE wide takes (shots 6, 18, 20) read in sync, at -2 to
  -78 ms and confidence 5.5-9.4.
- Rows: `docs/data/sync-calibration/warm-wide-min0.jsonl`.

**Shrink test (truth by construction).** Four in-sync Clown Sighting clips (shots 2, 7, 11 and 16; faces 15-32% of
the frame; offsets -62 to -5 ms) were scaled down onto a grey 704x1280 canvas, so that the only mouth is the small
one. Each got a planted audio delay of 200 ms and an advance of 160 ms. Rows: `evidence/floor*.jsonl`,
`floor_measure.py`, `scale_test2.py`.

| face height | S3FD at 0.25 (v2) | S3FD at 1.0 |
|---|---|---|
| 8% / 6% / 4.5% (100 / 77 / 58 px) | 25/25 within 7 ms, conf 8.4-10.5 | - |
| 3.5% (45 px) | 6/9 within 5 ms; 3 "no face found" | - |
| 2.5% (about 26-32 px) | 0/9: "no face found" | 9/9 within 4 ms, conf 8.0-10.1 |
| 1.8% (about 23 px) | - | 4/4 within 6 ms, conf 8.3-9.0 |
| 1.4% (about 18 px) | - | within 7 ms, conf 6.5 |

- **Every miss was the face detector, not SyncNet.** S3FD's smallest anchor is 16 px, and v2 ran it at 0.25 scale
  on 1280-px frames, so it never saw a face under about 64 px.
- **Controls.** Frozen mouths and swapped voices at 2.5-6% face height (`controls_measure.py`, `evidence/controls.jsonl`)
  all FAIL: frozen conf 2.3-2.5 (no sync peak), swapped conf 1.3 (and the words do not match).

**Meter v3 changes.**
- **Detection scale:** S3FD runs at 0.5, and at 1.0 when the largest face in six probe frames is under 96 px or no
  face is found.
- **Size floor in pixels:** `min_face_px` 32 replaces the 10% share. The floor has margin: 18-23 px still reads
  within 7 ms.
- **The size is no longer a reason to refuse a shot.**
- **Speed:** this costs about 2-3x the detection time on small-face clips; a close-up stays at 0.5.

**Another face mouthing the line (cause M9).**
- **Why:** the LTX-2 report says its audio-video attention carries time, not place. In MTAVG-Bench, human raters
  found the line in the right speaker's mouth in 24% of LTX-2.3's multi-speaker clips (Sora 2: 75%).
- **The check:** a second face track that is on screen together with the speaker for at least 30% of the voice and
  follows it at the speaker's offset (within 2 frames, confidence at least 4.2) is a FAIL.
- **Our footage so far:** across the survey's multi-face clips no second track followed the voice. The shot lab
  (P1, P3, P4) tests it.

**What v3 still cannot do.**
- It cannot tell *which* person the speaking face is: a take where the wrong character speaks, alone, still passes.
  The lab checks that by eye from the speaker box. An active-speaker model (LR-ASD, MIT) or a cast-portrait match
  would close it.
- Profiles are measured, but are uncalibrated. SyncNet's error on short samples rises from 13% frontal to 22% in
  profile (Chung & Zisserman 2017).
