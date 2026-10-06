# The film rig is one apparatus, and this repo is its home (a design rule, 2026-09-27)

**The rule.** Everything that makes the local film rig work, or records what it learned, lives in this git repo, or
is a symlink into it, or is a pinned, named dependency whose recipe lives here. Nothing that shapes a film may live
only in a scratchpad, a chat, a hand-made link or someone's memory. Change the rig by committing here, one commit
per change (`local-video: <what>`), with the evidence in the commit message.

Check it any time: `bin/apparatus check` (the links, the pins, the models, a clean tree). `bin/apparatus link`
re-creates every link; `setup.sh` calls it.

## One start, no model juggling (2026-09-27)

A film starts one way: pi on the local vision model (`rig/film-pi.sh -m vision-q4`) and a skill (`/skill:studio`,
or `/skill:film`). From there the local model orchestrates, and every other model is swapped in and out by the rig's
tools, never by a person and never by the director's bash:

| step | model | who loads and unloads it |
|---|---|---|
| directing, planning, reviewing | DeepSeek V4 Flash Vision (`vision-q4`, ds4 behind llama-swap, ~93 GB) | llama-swap loads it on the director's next request; `render_and_wait`, `redo_scenes` take the Mac's GPU hold (local-rig's hold gate on :8090, 2026-10-04), which lets other sessions' calls finish and unloads it before any GPU job; while held, every pi session waits and other clients are refused |
| cast portraits, first frames (`[still]`, `[place]`, `[cast]`) | Qwen-Image-2.1, FLUX.2 klein 4B (mflux) | `stories/story.sh` through `bin/still`, inside the render, one at a time |
| video and its audio | LTX-2.5 (ltx-2-mlx) | `stories/story.sh` through `bin/vidgen` |
| transcripts | Parakeet v3 (mlx-audio) | `rig/precheck.py --transcribe`, called by the render tools while the director is unloaded |
| faces, lip sync, pixel checks | macOS Vision on the CPU, ffmpeg | `rig/precheck.py`, `rig/review_images.py`, `rig/audit/lipsync.py` (uncalibrated, 2026-09-27: `docs/dialogue-sync.md`), `rig/sync/make_controls.py` (planted-truth controls for any sync meter) |
| dialogue sync gate (2026-09-27, iteration 5) | Demucs, S3FD, SyncNet v2, MediaPipe Face Landmarker, torchaudio MMS_FA on the CPU (`~/.cache/local-video/sync-venv`, recipe `rig/sync/setup.sh`) | `stories/story.sh` after each dialogue clip and before the stitch (`rig/sync/gate.py` → `rig/sync/syncmeter.py`); the pre-check prints its lines; `rig/sync/whospoke.py` (same instruments, 2026-10-04) draws who spoke for the review, from the render tools |
| delivery meter | the same venv + audeering wav2vec2 MSP-dim (arousal/valence), parselmouth | `rig/sync/delivery.py`, run by Claude for KPIs |
| character voices (audio-first dialogue) | Qwen3-TTS 1.7B VoiceDesign on MLX (mlx-audio's venv) | `rig/voice/tts.py`, on the GPU only between renders |

A new model joins the rig only this way: a recipe here (`rig/keyframe/setup-imagegen.sh` or `setup.sh`), a call
inside a tool or `story.sh`, and a line in this table. The director's prompt says it never starts or stops a model;
the bash guard blocks it from trying.

## What lives where

| part | where | versioned how |
|---|---|---|
| render command, stitch, redo, pre-check, review images, still drawing | `bin/`, `stories/`, `rig/` | this repo |
| the director: pi extension (tools, hooks, guards), director prompt, launcher, pi settings | `rig/film-rig.ts`, `rig/film-director.md`, `rig/film-pi.sh`, `.pi/settings.json` | this repo |
| skills for Claude Code and pi (studio, film, look-dev, cast, scene-breakdown, movie-prompt, vidgen) | `skills/` | this repo; `~/.claude/skills/*` and `~/.pi/agent/skills/*` are links into it |
| pi's extension and agent entries | `~/.pi/agent/extensions/film-rig.ts`, `~/.pi/agent/agents/film-director.md` | links into this repo |
| prompt rules with their evidence | `skills/film/references/prompt-rules.md` | this repo |
| projects, looks, cast, reference frames | `stories/projects/`, `stories/looks/`, `stories/characters/`, `stories/refs/` | this repo (the director commits its own) |
| benches, answer keys, test harnesses | `rig/bench/`, `rig/tests/`, `rig/audit/` | this repo |
| each iteration's brief, answer key, event log, interventions and fixes-after list | `rig/iterations/<date>-<name>/` in the working repo (not part of this public export; the measured data behind the README charts is in `docs/data/`) | git |
| the video engine | `~/repos/ltx-2-mlx` | upstream clone, never edited; pinned commit in `bin/apparatus` |
| the GPU hold: one lock for renders, m3d and the human's `hold on`; pi's waiting side | `~/repos/local-rig/hold` (the gate on :8090, llama-swap behind it), `~/repos/local-rig/extensions/hold.ts` (global, and loaded by `rig/film-pi.sh`); `stories/run-queue.sh`, `redo.sh`, `story.sh`, `bin/vidgen`, `bin/still` and the render tools take it | local-rig's git repo; `docs/hold.md` there |
| the language-model server | `~/repos/ds4` (fork of antirez/ds4, branch `fork`); the installed `ds4-server` is the `imgcache` build from worktree `~/repos/ds4-imgcache` | its own git repo; binary sha pinned in `bin/apparatus`, backup `ds4-server.pre-imgcache` |
| llama-swap config and pi's model catalog generator | `~/repos/local-rig` (`config/llama-swap.yaml`, `tools/gen-pi-models.py`) | its own git repo |
| the image models (Qwen-Image-2.1, Z-Image Turbo, FLUX.2 klein 4B) | `~/repos/imagegen/.venv`, `~/.cache/huggingface/hub` | not in git (tens of GB); recipe `rig/keyframe/setup-imagegen.sh`, choice in `rig/keyframe/IMAGE-MODEL.md` |
| LTX-2.5 weights | `~/models/ltx-2.5-mlx-q8` | not in git (70 GB); `setup.sh` |
| rendered clips, stills, contact sheets, sidecars | `~/Videos/vidgen/<film>/` | not in git (large media, `*.mp4` ignored); every clip has a JSON sidecar with its exact prompt, seed and mode, so it can be re-rendered from the repo |
| what each run proved, numbers, KPIs, action items | a private design wiki (summaries: `docs/`) | its own git repo |

## Rules that keep it one apparatus

- **A new external path** (a skill, an extension, a command on PATH) goes into `LINKS` in `bin/apparatus`, never by
  hand.
- **A new dependency** gets a pin or a recipe here, and a line in the table above.
- **The scratchpad is not a home.** At the end of an iteration, copy its brief, handoff, answer key, events,
  interventions and fixes-after list into `rig/iterations/`, and commit.
- **The director's own work is committed by the director** (projects, looks, cast). Claude commits rig changes.
- **The design notes hold the judgement; the repo holds the machine.** Each iteration write-up links the commits it tested.
