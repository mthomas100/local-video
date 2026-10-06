# Iterations: what each film taught the rig

Each film was a test of the rig, judged with numbers: an answer key written from the frames before the director's
own verdicts were read, the sync meter, the drift check, the run's timings and the interventions log. The full
iteration logs (briefs, event logs, interventions, fixes-after lists) are kept outside this public export; this is
the summary. Data behind the README charts: [`docs/data/`](data/).

| date | film | directed by | what it changed |
|---|---|---|---|
| 2026-09-22 | first clips | `vidgen` by hand | LTX-2.5 int8 on ltx-2-mlx chosen and measured: 56 s for 5 s at 480p, 177 s at 720p, audio in the same pass |
| 2026-09-23 | nine short fairy tales overnight | Claude Code | the long-form template (`stories/story.sh`): one style sentence and seed per film, a face frame from an earlier scene as the anchor; the style bible moved after the scene; 480p because a 720p 15 s scene took 16 min |
| 2026-09-23 | San Francisco 2060 (12 x 15 s) | pi on DeepSeek V4 Flash Vision, hands-off | the alternation design works (11 model requests, 2 sleep/wake cycles, no compaction); semantic review was the weak spot (look-alike landmarks passed) until the tools printed what each row was asked to show |
| 2026-09-24 | nyc-2000-slavic-neon | pi | post-mortem: images inside tool results made every wake re-read the whole context (about 21 min of a 114 min run), so render results became text only and sheets are shown once; the pre-check gained hard REDO verdicts (bars, borders, masks) after a letterboxed scene was waved through |
| 2026-09-25 | halloween-clowns-sf | pi | the director kept clear misses and asked to redo strong shots; `rig/bench/review-bench.py` replays the review step offline against an answer key |
| 2026-09-26 | halloween-clowns-sf-portrait (iteration 3) | pi | keyframe-first: `bin/still` draws every shot's first frame (Qwen-Image-2.1) before LTX animates it |
| 2026-09-27 | liminal-clowns (iteration 4) | pi | reference places and cast portraits (`[place]`, `[cast]`, FLUX.2 klein); per-film KPIs; the first lip-sync meter found uncalibrated |
| 2026-09-27 | Warm (iteration 5) | pi | the calibrated sync meter and the gate (13/13 lines per shot after retakes and rewrites); the delivery meter |
| 2026-10-03 | Clown Sighting (iteration 6) | pi, from Claude's screenplay | 19/19 lines in sync on the first take; the stitch drift found and fixed (0 ms) |
| 2026-10-03 | Thorns and Static (iteration 7) | pi, from Claude's screenplay | 5/5 lines in sync from close-up to full length; pre-check false REDOs on a dark palette (8) |
| 2026-10-03/04 | the shot lab | pi renders, Claude measures | 35 kinds of speaking shot, 66/69 first takes in sync; meter v3 (32 px faces, a second mouth, per-line exchanges); `[hold]` and `[layout]` tokens |
| 2026-10-04 | The Garden of Teeth (iteration 8) | pi, from Claude's screenplay | one face in every shot (`[cast]` on 18/18 face shots), 4/4 lines in sync, 0 false pre-check REDOs, 212 min wall |
| 2026-10-04 | The Last Car (shot lab phase C) | pi wrote and directed it | 8/8 lines in sync on the first take across six kinds of speaking shot |
| 2026-10-04 | iteration 9 (film not published) | pi on Qwen3.8 | per-shot lengths (5-15 s); the Mac-wide GPU hold; 4/8 lines on the first take, 2 never in sync (accepted as exceptions); a who-spoke image added to the review after a line landed in the wrong mouth |

## The recurring lessons

- **Measure the instrument before trusting it.** The first lip-sync meter, the 10% face floor and the per-shot
  "in sync" counts were each wrong in a way only a planted control or a whole-film check could show.
- **The local model directs; the harness makes it safe.** Every failure that cost real time (a stray server beside a
  render, image re-reads, a director that kept a miss) was fixed in the tools and the prompt, not by watching.
- **Write so that nothing is left to the video model.** The three films made from a full screenplay that applied the
  measured speaking-shot rules (every shot's place, people, framing, the exact line, the face cue, the delivery)
  passed 28 of 28 lines on the first take; Warm, planned shot by shot, passed 10 of 13.
