# rig — a local model directs the film loop on this Mac (2026-09-23)

The goal: switch the internet off and watch a local agent coordinate with a local video model. This folder is that agent: a `pi` session on a local vision LLM
(DeepSeek V4 Flash Vision-Exp through llama-swap, or Qwen3.8-27B) that interviews, writes a
project file, renders it with LTX-2.5 through `stories/run-queue.sh`, reviews contact sheets,
and re-renders the scenes that missed, the way Claude Code did for the nine films of
2026-09-23 (`skills/film/SKILL.md`). The design notes are in
`docs/architecture.md`.

The one hard fact it is built around: the LLM and the renderer cannot share the GPU. A model
prompted beside a render slows the render 9x and never answers; a big model idle beside a
render is over the memory budget (the overnight-run notes (not published)). So the loop alternates: the model
writes, a tool unloads the model and renders, the model is reloaded on its next reply, and
ds4's disk KV checkpoints (`~/.ds4/kv-disk`) make that reload a suffix prefill rather than a
full one. Measured numbers: `MEASUREMENTS.md`.

## Files

| file | what |
|---|---|
| `film-rig.ts` | the pi extension: tools `render_and_wait`, `review_scenes`, `redo_scenes`; guards (bash cannot start renders or touch model servers, while `ls`/`open`/`ffprobe`/`afplay` on `~/Videos/vidgen/...` work; an LLM call is held while any render process exists; compaction is cancelled during a render); context shaping (a contact sheet is shown once, then replaced by a note; reasoning from before the latest compaction is dropped); `/skill:studio` and `/skill:film` switch director mode on; `/rig` shows the preflight. Symlinked as `~/.pi/agent/extensions/film-rig.ts`. |
| `precheck.py` | model-free checks per scene from six sampled frames: black bars (uniform-black rows or columns, per frame), border, mask (also mid-clip), vignette, faces vs the people the scene names (macOS Vision), brightness, motion; cartoon statistics are reported but do not flag. Verdicts: `REDO` (hard: bars, border, mask, frozen, black), `LOOK` (soft), `OK`. `--transcribe` adds what the audio says (`transcribe.py`, Parakeet v3, GPU: the render tools call it while the model is unloaded). Cached per scene in `<film>/.precheck/`. |
| `transcribe.py` | Parakeet TDT 0.6B v3 on mlx-audio's venv: `{clip: text}` for a list of clips (English and 24 European languages). |
| `film-director.md` | the system prompt: the loop, the sheet checklist, the writing rules, the rules never to break. Also an agent definition for pi's subagent extension (`~/.pi/agent/agents/film-director.md`). |
| `film-pi.sh` | the launcher: `pi --offline`, this extension only, the prompt appended, the tool allowlist. |
| `MEASUREMENTS.md` | experiment numbers (wake cost, co-resident render cost, streaming). |
| `audit/` | watching a film run live and judging it with numbers: `run-metrics.py`, `watch-pi.sh`, `sample-mem.sh`, `capture-upstream.sh` (see `audit/README.md`). |

The runner scripts gained two small things for the rig: `stories/story.sh` stops cleanly before
the next scene when `~/Videos/vidgen/<NAME>/stop-after` holds a scene number (exit 3), and
`stories/run-queue.sh` logs `PAUSED <name>` for that, `OK`/`FAILED` otherwise.

## Start it

    cd ~/repos/local-video
    rig/film-pi.sh                       # DeepSeek Vision Q2/Q4 (vision-q4-400k), alternation mode (recommended);
                                         # then type: /skill:studio <brief>   (or /film <brief>)
    rig/film-pi.sh -m qwen27-262k --resident  # Qwen 27B kept loaded beside 480p renders (experiment)
    rig/film-pi.sh -c                    # continue the last session (the film survives a restart:
                                         # everything is on disk; finished scenes are skipped)

## Or from any pi session: `/film`

    /film a cat who becomes an app developer      # director mode on, brief sent, interview follows
    /film                                         # director mode on; then describe the film
    /film status                                  # GPU preflight, lifecycle, model, director on/off
    /film off                                     # leave director mode

Works natively with whatever model the session already has, as long as it can see images (the
command warns if it cannot; DeepSeek Flash Vision and Qwen 27B can). The extension is auto-loaded
from `~/.pi/agent/extensions/film-rig.ts`; `/film` appends `rig/film-director.md` to the system
prompt on every turn, remembers the choice in the session (so `pi -c` resumes in director mode),
and picks the model lifecycle from the model's provider: `local/*` is llama-swap (unload before a
render, reload on the next reply); `ds4/*` or `qwen/*` means you started the engine with `model
<target>`, so the render tool runs `model stop` before a render and `model <target>` after it,
and your next reply works. The launcher below only adds `--offline`, the tool allowlist and the
prompt up front; it is not required.

Do not run the `model` command (ds4-serve) while using the rig: it starts its own engine on :8000
outside llama-swap, which the render tools refuse to work beside, and it rewrites pi's catalog
(since 2026-09-23 it merges, keeping the `local` provider; before that it replaced the file).
`film-pi.sh` regenerates the catalog if needed and refuses beside a stray server.

Then give it the brief in one message. It asks its interview questions once (length, size,
mode, style); answer briefly; then leave it alone. A 480p 8-scene film is about an hour, a
720p portrait 12-scene film about 3.5 hours, and the model sleeps through all of it.

Requirements, all local: llama-swap on `127.0.0.1:8090` (launchd `com.example.llama-swap`)
with the generated config; the pi catalog generated by
`~/repos/local-rig/tools/gen-pi-models.py` (it lists `vision-500k`, `vision-q4-400k`, `qwen38` and the Qwen 27B rows with
image input; running `./ds4-serve <target>` overwrites it, re-run the generator); `vidgen` and
the LTX-2.5 pack; `ffmpeg`; the engine venv's Python (numpy, Pillow) which `precheck.py`
re-execs into. Nothing contacts the network: pi runs with `--offline`, models load from disk.

## With the internet off

Nothing in the loop needs it. Check before unplugging: `curl -s 127.0.0.1:8090/running`
answers, `pi --list-models local` lists `local/vision-q4-400k`, and `vidgen --dry-run "x"` prints an
engine command. Hugging Face and npm are never contacted at run time.

## The GPU rules (the extension enforces them; know them anyway)

1. One render at a time. `pgrep -f "ltx-2-mlx generat[e]"` must be empty before anything
   starts. The tools refuse otherwise.
2. No LLM on the GPU during a render. In alternation mode the tool calls `GET /unload` and
   waits until `/running` is empty, no `ds4-server`/`llama-server` process exists and wired
   memory is under 40 GB (`FILM_RIG_WIRED_MAX_GB`). In resident mode it waits only for stray
   ds4 servers; Qwen stays loaded and nothing prompts it until the tool returns.
3. Never SIGKILL a model server (Metal memory can leak until reboot); the extension never
   kills anything, and bash `kill`/`pkill` are blocked for the agent.
4. Never poll a render with a model turn. The tool blocks the turn; the `context` hook holds
   any model call while a render process exists, even one started by someone else.
5. Same text + same seed = the same clip; a redo must change one of them.

## How the pieces talk

    pi (local/vision-q4-400k) ──tool call──▶ film-rig.ts ──GET /unload──▶ llama-swap (evicts ds4-server, ≤240 s)
                                                │ waits: /running empty, wired < 40 GB
                                                │ spawns detached: zsh stories/run-queue.sh <project>
                                                │ polls logs/queue.log for OK|FAILED|PAUSED <NAME>
                                                │ sheet.sh + precheck.py (CPU) + transcribe.py (GPU, model still unloaded)
    pi ◀──tool result: TEXT only────────────────┘
    pi ──next request──▶ llama-swap loads the DeepSeek model (13-17 s) ──▶ ds4-server restores the KV prefix from disk
    pi ──review_scenes──▶ sheets as images, shown once (the context hook replaces them after the reply)

Why text only (2026-09-24): ds4-server skips its disk KV cache for any request that carries an
image, and re-reads an image-bearing request from token 0 when its live cache mismatches at the
model's own first generated token. With the sheets inside the render result, every wake re-read
the whole context twice (about 21 min of a 114 min film run).

The "wake" is nothing but pi's next request. No cron, no watcher, no second process: the tool
blocks inside the turn, so no model call can happen until it returns.

## Modes

- `alternate` (default): the model is unloaded for every render. Costs one load plus a suffix
  prefill per render (numbers in MEASUREMENTS.md). Works with any model, including DeepSeek.
- `resident` (`--resident`, `FILM_RIG_MODE=resident`): the model stays loaded. Only fits
  `qwen27-262k` (measured as the old 131K `qwen27` row) beside 480p renders (about 35 + 28-35 GB of the 107.5 GB budget); DeepSeek resident
  is over budget. The blocking tool is the only thing preventing a prompt mid-render.

## Known limits

- Semantic judgment is the weak spot, not pixels: on the first hands-off film DeepSeek Vision
  passed a Giza pyramid for the Transamerica Pyramid and Big Ben for Coit Tower until the tools
  printed what each row was asked to show and the prompt named look-alikes as misses; after that
  it found and fixed all three on its own (MEASUREMENTS.md). Describe famous landmarks physically
  in the scene text from the start.

- The cartoon heuristic in `precheck.py` does not work; animation drift is judged from the sheet.
- Face counting counts every face Vision sees, extras included; the `faces>named` flag needs
  the scene to name its people the way the skill prescribes.
- `redo_scenes` finishes when `redo.sh` exits; it does not write `queue.log`. It renders only the
  named scenes (`ONLY=`), refuses a scene whose text and seed match its last take, and allows
  three takes per scene.
- The pi compaction reserve for this repo is in `.pi/settings.json` (8192, keep 16000); pi reads
  it only for a trusted project, so `film-pi.sh` passes `--approve` (a normal session asks once).
- Local models sometimes call `bash` for things the tools do; the guard blocks the dangerous
  ones and the reason text tells the model which tool to use instead.
