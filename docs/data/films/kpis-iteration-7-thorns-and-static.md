# Iteration 7 KPIs: "Thorns and Static" vs Clown Sighting (meter v3, 2026-10-03)

**Sources:**
- sync and delivery: `kpis-thorns-and-static.txt` (`measure-film.sh`; `sync-cal/thorns-and-static*.jsonl`)
- run: `film7/run-metrics.txt`, `film7/session-timeline.jsonl`, `events.md`, `interventions.md`
- pre-check: `evidence/precheck-false-positives.md`

**The film:** `~/Videos/vidgen/thorns-and-static/thorns-and-static.mp4`.
- 171.0 s, 24 shots, 704x1280 portrait at 24 fps; 5 shots have dialogue (one speaker, Zorya).
- First cut (before the redos) kept as `thorns-and-static-cut1.mp4`.
- Script: Claude wrote the whole screenplay (`stories/screenplays/thorns-and-static.md`).
- Director: pi on DeepSeek V4 Flash Vision (`vision-q4-400k`), 14:52-19:40 (287 min).

## Dialogue sync (the interim speaking-shot rules, 6b867dd)

| shot | framing | face | raw clip | final cut (as played) |
|---|---|---|---|---|
| 3 (redo) | medium close-up | 228 px | PASS -40 ms, conf 10.98 | PASS -46 ms, conf 9.94 |
| 7 | full length (asked knees up) | 82 px | PASS -24 ms, conf 7.37 | PASS -5 ms, conf 6.22 |
| 12 | close-up | 410 px | PASS -46 ms, conf 9.16 | PASS -33 ms, conf 8.13 |
| 14 (redo) | waist up, push-in | 205 px | PASS -43 ms, conf 9.38 | PASS -35 ms, conf 7.93 |
| 19 | knees up | 217 px | PASS -31 ms, conf 7.33 | PASS -21 ms, conf 4.77 |

| | Clown Sighting (it. 6) | Thorns and Static (it. 7) |
|---|---|---|
| dialogue shots PASS, first take | 19/19 | **5/5** (and both redone lines: 2/2) |
| final cut PASS as played | 19/19 | **5/5** |
| final minus raw | within 21 ms | **-6..+19 ms** |
| drift at the end (`drift.py`) | 0 ms | **0 ms** (0 audio and 0 video gaps) |
| framings that spoke | medium close-up only | **close-up to full length** |

- **This is the first film made under the interim speaking-shot rules.** Every framing from a close-up to a full-length
  82 px face passed on the first take.
- **Weakest:** the final-cut confidence of shot 19 (4.77; the gate's floor is 4.2). That cut is a knees-up shot of a
  speaker backlit by a sunset. Its raw clip reads 7.33.

## Delivery and silent articulation

| | Clown Sighting | Thorns and Static |
|---|---|---|
| mean arousal (neutral band 0.41-0.60) | 0.735 | **0.492** |
| lines above the neutral band | 19/19 | 1/5 (shot 14, 0.644) |
| lips moving without the voice, max | 0.42 s | **0.17 s** |
| words per second | - | 1.87-2.13 |

- **The low arousal was written that way.** The delivery cues asked for "low and dry", "cool and contemptuous, almost
  bored", "quiet and wondering", "flat and brittle" and "soft and unsteady". Only shot 14's exasperation rose above
  the band.
- **The meter is a proxy, not a judge of acting.** On Claude's frame review the acting reads strongest in 12 (fear) and
  14 (exasperation).

## Director (pi) run

| | Clown Sighting | Thorns and Static |
|---|---|---|
| wall time | 221 min | 287 min |
| planning to first render | 36 min | **20 min** (14:52 to the cast portrait at 15:12) |
| render | 65 + 94 min, no redos | 31 + 142 min; redos 16 min (paused) + 32 min |
| model replies / output tokens | 45 / 75,902 | 44 / 60,337 |
| peak context / compactions | 139,623 / 0 | 121,658 / 0 |
| length stops / bad stops | 0 | 0 |
| lines copied word for word | 22/22 shots | **24/24 shots**, 5/5 lines (compare_lines.py) |
| interventions after the prompt | 0 | **1 steering message + 1 rig action (stop-after)** |

**Why the intervention:** pi's full review did two things wrong.
- It sent 8 good takes to a redo on pre-check false positives (`bars:letterbox`, `black-frames` on a dark palette).
- It kept 3 real misses: 3, 14 and 22.

On Claude's list of 4 misses (3, 6, 14, 22) pi's own review caught 1 (6). After the steering message it applied every
rewrite word for word, restored the 8 takes and finished without further help.

## Claude's own screenplay errors

- Two light phrases were painted onto her skin by the image model (shots 3 and 14).
- One shot's peak was never put in the opening still (shot 22, the surge).
- All three were fixed by redo, and the rule is now in the screenplay skill (acae9d6).
