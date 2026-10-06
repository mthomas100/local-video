# Iteration 6 KPIs: "Clown Sighting" vs Warm and liminal-clowns (meter v2, 2026-10-03)

**Sources:**
- sync and delivery: `kpis-clown-sighting.txt` (`measure-film.sh`; `sync-cal/clown-sighting*.jsonl`)
- drift: `sync-drift/README.md`, `rig/sync/drift.py`
- run: `film6/run-metrics.txt`, `film6/session-timeline.jsonl`, `events.md`, `interventions.md`

**The film:** `~/Videos/vidgen/clown-sighting/clown-sighting.mp4`.
- 174.9 s, 22 shots, 704x1280 portrait at 24 fps; 19 of the shots have dialogue.
- Script: Claude wrote the whole screenplay (`screenplay.md`): every shot, line, delivery, background action and
  sound.
- Director: pi on DeepSeek V4 Flash Vision (`vision-q4-400k`), 02:00-05:41 (221 min).

## Dialogue sync

| | liminal-clowns (it. 4) | Warm (it. 5) | Clown Sighting (it. 6) |
|---|---|---|---|
| dialogue shots PASS (per shot) | 9/10 | 13/13 | **19/19** |
| passed on the first take | - | 10/13 | **19/19** |
| dialogue renders per dialogue shot | - | 28/13 | **19/19** |
| raw offset, median (conf >= 5) | -41 ms | -19 ms | -34 ms (range -62..+2) |
| **film as played (voice early at the end, `drift.py`)** | **1980 ms** | **2160 ms** | **0 ms** |

- **The drift row is the iteration's finding.** Every earlier film drifted ~90 ms per cut, so its final-cut "PASS"
  counts held for the clips only (`sync-drift/README.md`).
- **Clown Sighting checked as Apple players play it:**
  - AVFoundation: 174.94 s of audio for 174.92 s of video.
  - SyncNet on player-view windows at 8, 70, 127, 151 and 159 s: -61, -2, -43, -37 and -33 ms, all PASS.
- **Why every line passed first time:** the screenplay applied iteration 5's measured rules on every speaking shot.
  - one speaker;
  - a medium close-up or close-up;
  - the microphone below the chin;
  - 12-16 words for 8 s;
  - a face cue before the speech verb;
  - no speech in the first instant.

## Delivery and silent articulation

| | liminal-clowns | Warm | Clown Sighting |
|---|---|---|---|
| mean arousal (neutral band 0.41-0.60) | 0.598 | 0.566 | **0.735** |
| lines above the neutral band | - | - | 19/19 |
| lips moving without the voice, max | 0.75 s | 0.25 s | 0.42 s |

- **Delivery rose a lot.** Each line had a playable delivery cue in the screenplay ("flat and aggrieved, slowing on
  'four hours'"), and the genre helps: interviewees and a reporter, not "low and flat" clowns.
- **The meter is a proxy, not a judge of acting.**

## Director (pi) run

| | Warm | Clown Sighting |
|---|---|---|
| wall time | 390 min | **221 min** |
| planning to first render | 44 min | 36 min |
| render | 214 min + 80 min redos | 65 + 94 min, **no redos** |
| model replies / output tokens | 64 / 130,107 | 45 / 75,902 |
| peak context / compactions | 78,088 / 2 | 139,623 / **0** (384K row) |
| length stops / nudges from Claude | 3 / 2 | **0 / 0** |
| lint refusals | 1 | 0 |
| interventions after the prompt | 2 | **0** |

**Fidelity:** pi copied all 22 shots in order and all 19 spoken lines word for word (checked with a script against
`screenplay.md`), with every token as marked.

## Film quality (Claude's frame review)

**Strong:**
- the San Francisco places read as themselves:
  - the Transamerica Pyramid, the Bay Bridge and fog (1);
  - the Golden Gate Bridge from Crissy Field (15);
  - the Ferry Building clock tower (19, 20);
  - Pier 39's sea lions with Alcatraz (11);
  - pastel Victorians;
- the Halloween dressing is in every outdoor shot (jack-o'-lanterns, cobwebs, papel picado, a skeleton hoodie);
- the clown holds one look in all 20 shots he is in;
- Gloria, Kevin and Pruitt each keep one face;
- the clown's background gag is visible in every interview, and nobody looks at him;
- the payoff shot (22) is as written: the clown in a navy jacket at the weather wall, a jack-o'-lantern, the fog
  sweep and the thumbs up.

**Misses:**
- the clown is drawn mid-ground and in focus, not "far ... out of focus" (better for the joke);
- shot 18 puts him right beside Pruitt;
- shot 20 draws him a little large;
- text is garbled: a microphone flag reads "2" (14), and the shop sign (12);
- the weather map is a generic coastline (22);
- 2, 3 and 21 carry LOOK flags from the dark studio (no real bars).

**pi's review** called all 22 keep and named the shot-20 size; it did not mention 18's placement or the text. With
no real misses to redo, that cost nothing.
