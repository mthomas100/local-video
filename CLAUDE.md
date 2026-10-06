# local-video: notes for Claude Code sessions

This repo is the whole local film rig, one apparatus under version control. Read `APPARATUS.md` first, and run
`bin/apparatus check` before and after changing anything. pi never sees this file: `rig/film-pi.sh` passes
`--no-context-files`, so the director's inputs are only `rig/film-director.md`, the skills and the tools.

- Commit every rig change on its own as `local-video: <what>`, with the evidence in the message.
- The local model directs; Claude improves the harness and judges. Log every input you give a running director.
- Never read, print or quote the local model's thinking or `reasoning_content` (pi session files, API payloads).
  Use `rig/audit/last-replies.py` (visible text and tool calls) and `rig/audit/session-timeline.py`.
- One GPU job at a time; never SIGKILL a model server; unload with `curl -s 127.0.0.1:8090/unload`.
- **Dialogue rules (the shot lab, 2026-10-03/04):** write any speaking shot.
  - 66 of 69 lab first takes were in sync across 35 shot types, and pi's own varied scene went 8/8.
  - The only limits are WHO speaks (a name before the verb, others silent) and a speaking face under ~50-100 px.
  - `[hold]` keeps a wide speaker wide; `[layout]` draws `[cast]` small.
  - The gate is meter v3: faces from 32 px, a second mouth following the voice fails, exchanges checked per line.
  - Rules: `rig/film-director.md` DIALOGUE and `skills/film/references/dialogue-shots.md`. Evidence:
    `docs/data/shot-lab/` and `docs/dialogue-sync.md`.
- **Iteration 8 (2026-10-04): "The Garden of Teeth"**, Thorns and Static retold as one story with one face. `[cast]`
  was on all 18 face shots and every line was in sync; the fixed pre-check wasted no renders. Open: instant events in
  `[still]`+`[cast]` shots.
- Iteration 7 (2026-10-03): "Thorns and Static", 5/5 lines in sync on the first take from close-up to full length
  (82 px face); 0 ms drift. Its misses were in the picture, in the review and in the pre-check (false letterbox and
  black-frame REDOs on a dark palette).
- Iteration 6 (2026-10-03): "Clown Sighting", 19/19 dialogue shots in sync on the first take, and the drift root
  cause fixed (the stitch left a ~90 ms audio gap at every cut): `docs/data/sync-drift/README.md`.
- The iteration logs themselves are kept outside this public export; `docs/iterations.md` summarises them.
