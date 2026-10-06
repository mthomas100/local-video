# Iteration 8 KPIs: "The Garden of Teeth" vs Thorns and Static (meter v3, 2026-10-04)

**Sources:** `kpis-garden-of-teeth.txt` (measure-film.sh), `film8/run-metrics.txt`, `events.md`, `interventions.md`.

**The film:** `~/Videos/vidgen/garden-of-teeth/garden-of-teeth.mp4`.
- 169.0 s, 24 shots, 704x1280 portrait.
- First cut, before the redos of 18 and 22: `garden-of-teeth-cut1.mp4`.
- Script: Claude's screenplay. Director: pi on vision-q4-400k, 21:11-00:43 (212 min).

| | Thorns and Static (it. 7) | The Garden of Teeth (it. 8) |
|---|---|---|
| on-screen dialogue PASS, first take | 5/5 | **4/4** (+ 1 off-screen voice, gate: OFFSCREEN) |
| final cut PASS as played | 5/5 | **4/4** (-35, -68, -71, -5 ms) |
| final minus raw | -6..+19 ms | **-21..+9 ms** |
| drift (`drift.py`) | 0 ms | **0 ms** |
| lips moving without the voice, max | 0.17 s | 0.21 s |
| mean arousal (neutral band 0.41-0.60) | 0.492 | 0.443 (the lines were directed quiet; 15 "hope breaking through" 0.71) |
| shots that show her face with `[cast]` | 9/24 | **18/18** |
| her face, on Claude's frame checks | other women in 5, 9, 13, 16; fang points at the lips in 12, 14, 19 | **one face, clean, in every shot** (one duplicate of her in 18, take 1) |
| pre-check REDOs that were false | 8 | **0** (f9c6902) |
| wall time / planning to first render | 287 / 20 min | **212 / 8 min** |
| model replies / output tokens | 44 / 60,337 | **26 / 30,213** |
| redos | 3, 6, 14, 22 (+8 false, restored) | **18, 22** |
| interventions after the prompt | 1 message + 1 rig action | **1 message** (shot 18) |

- **measure-film's backmeasure ignores `[offscreen]`.** It lists shot 4 as UNMEASURABLE ("speaker not visible"), which
  is the intended staging. The render gate handled it right.
