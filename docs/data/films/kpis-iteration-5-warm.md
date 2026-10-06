# Iteration 5 KPIs: "Warm" vs the liminal-clowns baseline (meter v2, 2026-09-28)

Sources:
- sync and delivery: `kpis-warm.txt` (measure-film.sh; sync-cal/warm*.jsonl), baseline `kpis-liminal-clowns-v2.txt`
- run: `film5/run-metrics.txt`, `film5/session-timeline-warm.jsonl`, `events.md`, `interventions.md`
- review: `film5/answer-key.md` (Claude's frame review, written before pi's verdicts)
- side analyses: `side-analyses/`

Film: `~/Videos/vidgen/warm/warm.mp4`, 191.4 s, 24 shots, 720p portrait, 13 dialogue shots. pi (DeepSeek V4 Flash
Vision, `vision-q4`) directed from 17:35 to 00:05 (390 min).

## Dialogue sync (the iteration's goal)

| | liminal-clowns (iteration 4) | Warm (iteration 5, gate on) |
|---|---|---|
| final cut PASS | 9/10 | **13/13** |
| raw clip offset, median (conf >= 5) | -41 ms | -19 ms |
| stitch shift (final - raw) | +364 ms on one shot (the old nudge), else -8..+31 | -20..+33 ms (no nudge) |
| accepted sync exceptions / [offscreen] | - | 0 / 0 |

How the 13/13 was reached:
- **First pass:** 10/13 after the gate's automatic retakes. Shots 6, 18 and 20 stayed UNMEASURABLE after 3 takes each, so the stitch was refused (SYNCGATE, 22:21).
- **Shot 2** failed 6 takes over two rounds (conf 1.1-2.8) and passed on its first take once pi cut it to `[secs=5]`.
- **Shots 6, 18, 20:** pi rewrote them as close-ups, and each passed on its first take.
- **Cost:** 28 dialogue renders for 13 shots. The 15 extra fast renders are about 67 GPU-min.

Root cause of every failure:
- a 1-3-word line in an 8 s shot (shot 2);
- or the line spoken in the first second of a portrait medium or full-length shot, while the face is under 10 % of the frame height (6, 18, 20; checked, not a meter bug);
- plus a cup or phone at the mouth (2, 6).

The gate never passed a take it should not have; every refusal had a visible cause in the frames.

## Delivery and silent articulation

| | liminal-clowns | Warm |
|---|---|---|
| mean arousal (neutral band 0.41-0.60) | 0.598 | 0.566 |
| lines out of the neutral band | 6/10 | 7/13 |
| lips moving without the voice, max | 0.75 s | 0.25 s (shot 24) |

- **Delivery did not improve by this measure.** The mean arousal is lower.
- **Much of that is by design:** 5 of Reginald's 7 lines are directed "low and flat, even". His mean is 0.54 and Mopsy's 0.61.
- **The film's first line,** Mopsy's "Still warm." at 0.40, is the flattest.
- **Silent mouthing is lower,** well under the 0.75 s bar.

## Director (pi) run

| | Warm |
|---|---|
| wall time | 390 min (planning 44 min to the first render call; render 42.9 + 171.2 min; redos 14 + 2.8 + 53.2 + 10.1 min) |
| model replies / output tokens | 64 / 130,107 |
| peak context / compactions | 78,088 / 2 (19:07 at 77,213; 22:45 at 78,088), both right after a review_scenes result |
| length stops | 3: two with no output in planning (16,384 tokens, nudged at 17:53 and 18:04); one clamped at 5,078 tokens (22:41), recovered by compaction with no nudge |
| lint refusals | 1 (18:18, lines not directed; pi fixed them) |
| interventions | the interview answer (17:38) + 2 planning nudges; none from the render through the end |

Review accuracy against Claude's answer key (10 real misses):
- **Recall:** pi redid 7 of the 10 (2, 4, 6, 8, 17, 18, 20).
- **Missed:** 16, 21, 23.
  - 16 is a false keep: Agnes walks toward the lens.
  - 21 and 23 got no visible verdict: the review text for 20-24 was lost to the 22:41 length stop and the compaction. Both kept Reginald's absence, and 23 the missing turn.
- **Extra redos:** 5 and 9 had small real defects (balloons, extra figures), so neither was a false redo of a strong shot.
- **pi caught 17** (Reginald absent), which Claude missed.

Report truthfulness:
- **Sync:** every sync line was copied as printed.
- **Visual claims:** false on 21 ("balloon straining"), 23 ("three clowns turn to camera") and "the twist holds", and on 16. One confabulated detail right after a compaction (19:07, the cup "on the table").

## Film quality (Claude's review)

- **Strong:**
  - the six reference places held (all six photos used as `[place]`);
  - the cast portraits kept four stable identities in most shots;
  - the dialogue close-ups are clean and in sync.
- **Misses that survive in the cut:**
  - the balloon never grows (the motif is lost);
  - Agnes walks toward the camera in 8 (debatable) and 16;
  - the twist shot 23 has no turn and no Reginald;
  - 21 lacks Reginald;
  - identity drift on Reginald in 2 and 10 (a white ruff, a bare face);
  - two teddy bears in 13 and 14.

## What helped, what didn't
- **Helped:**
  - The gate in the render path: nothing out of sync reached the cut, and the refusal made pi fix exactly the refused shots.
  - Close-up framing and a short shot for a short line: every sync redo that changed the framing or the length passed on the first take.
  - `[place]` + `[cast]`.
- **Didn't help:**
  - The gate's seed retakes of a shot whose framing or line length was wrong: 0 of 10 passed.
  - The "directed" delivery cues: arousal didn't rise.
  - The 84K window: two compactions, and the reply-cap squeeze lost the last review batch.
- **Next:** the side analyses' first steps (the window fix; fewer quality shots and a stills-first review for time) plus the lint checks for short lines and small speaking faces (`fixes-after.md`).
