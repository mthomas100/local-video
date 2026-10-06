# Measurements for the local-agent film rig (2026-09-23)

Machine: M5 Max, 128 GB, macOS 27; Metal working-set budget about 107.5 GiB. llama-swap v255 on
`127.0.0.1:8090`; `vision` = DeepSeek V4 Flash Vision-Exp IQ2XXS via ds4-server with
`--kv-disk-dir ~/.ds4/kv-disk`; `qwen27` = Qwen3.8-27B Q5_K_M via llama-server with the vision
projector. Renderer: LTX-2.5 int8 on ltx-2-mlx, fast mode. Timestamps from `~/.ds4/llama-swap.log`,
`vm_stat`, and `logs/runs.tsv`. Raw scripts and logs of the experiments are in the session
scratchpad; the commands are reproduced here.

## E1: alternation wake cost (DeepSeek Vision, pi session, 30k-token context)

Setup: `rig/film-pi.sh -m vision --name e1-wake-cost` in tmux; the model read the film skill,
the prompt rules, the overnight-run notes (not published), README.md and six project files (pi status: 36.2% of
84k, about 30k tokens of context; `R80k` cache reads).

| step | measured |
|---|---|
| cold load of `vision` (first request of the session) | `matrix: model=vision starting` 16:49:25 → `Health check passed` 16:49:48: **23 s**; the first request (skill read, 38 KB reply body) completed in 44 s |
| a 24k-token turn (the reads) | request 60.6 s for ~24k prefill + ~700 output tokens |
| `curl 127.0.0.1:8090/unload` | returned after **2 s**; `/running` empty; ds4-server gone; wired memory **92.8 → 4.8 GB in 4 s**; ds4 wrote a new 441 MB checkpoint in `~/.ds4/kv-disk` at the unload |
| wake ("Say only OK." after the unload) | `model=vision starting` 16:52:23 → healthy 16:52:32: **9 s warm load**; the request completed in **10.5 s**; **13 s from sending the message to the answer on screen**; pi shows CH 100% (the whole prefix restored from the disk checkpoint) |

Verdict: the wake costs about 13 s, far under the minute the handoff set as the threshold for
using DeepSeek Vision as the orchestrator. Alternation is the rig's default mode. E3 (DeepSeek
under SSD streaming beside a render) was therefore not run.

Commands:

    rig/film-pi.sh -m vision --name e1-wake-cost        # in tmux; then the read prompts
    curl 127.0.0.1:8090/unload; vm_stat | grep wired    # unload, watch wired memory
    # send "Say only OK."; then:
    grep -E "vision starting|<vision>|chat/completions" ~/.ds4/llama-swap.log | tail -4

## E2: co-resident Qwen 27B beside a 480p 15 s render

Same prompt and seed (5) for every render, `vidgen --no-open --seconds 15 --size 480p --seed 5`,
outputs in `~/Videos/vidgen/rig-tests/`. Baseline measured in the same minutes, nothing loaded.

| case | render wall (vidgen sidecar) | notes |
|---|---|---|
| nothing loaded (baseline) | **158.5 s** | wired 4.8 GB before the render |
| `qwen27` loaded through llama-swap, idle | **154.4 s** | qwen27 loaded and answered a 5-token prompt in 13 s; wired 34.8 GB with it resident; no penalty at all |
| `qwen27` resident and PROMPTED with a contact sheet 45 s into the render (1171 prompt tokens incl. the image, 200 output tokens) | **166.9 s (+5%)** | Qwen answered in **79 s**, all of it thinking (finish=length at 200 tokens): about 2.5 tok/s beside the render |
| reference: the same sheet prompt with the GPU otherwise idle (600 output tokens) | | **33 s** including the 7-13 s load: about 30 tok/s |

Reading: with a clean GPU, a resident Qwen 27B costs the render nothing while idle and about 5%
while answering, but Qwen itself runs about 10x slower during a render (the "9x refine-step
slowdown, no answer in 4 min" of the night before was measured with a stray 90 GB ds4 server wired
beside both; see the overnight-run notes (not published)). So resident mode is viable for Qwen at 480p, the model
must still never be prompted mid-render (it would think for minutes), and the blocking tool is
what makes that impossible. Wired memory: 34.8 GB with Qwen resident, back to 4.9 GB after
`/unload`. Memory for 720p portrait (53 GB peak) beside Qwen (35 GB) stays under the 107.5 GB
budget on paper; not measured.

Commands: the script `e2.sh` in the session scratchpad; in short
`vidgen --no-open --seconds 15 --size 480p --seed 5 -o ~/Videos/vidgen/rig-tests/<case>.mp4 "<prompt>"`
three times, with `curl 127.0.0.1:8090/v1/chat/completions -d '{"model":"qwen27",...}'` before the
second (load) and 45 s into the third (an `image_url` data URI of a sheet PNG).

## E3: DeepSeek under SSD streaming beside a render

Not run: E1 made alternation cheap (13 s per wake), which the handoff set as the condition.

## Smoke test of the tools through pi (2026-09-23 17:04-17:11, `stories/projects/00-rig-smoke.txt`)

Two 5 s scenes at 480p on `vision`, driven by explicit instructions: `render_and_wait` with
`until_scene 1` (PAUSED cleanly, 45 s scene), `review_scenes` (the model described the sheet it
received as an image), `render_and_wait` to finish (OK, stitched), an `edit` of the project adding
`[seed=9]`, `redo_scenes 2` (old take kept in `redo-1/`), a correct report. Four sleep/wake cycles:
each `GET /unload` returned in 1.2-1.5 s, each reload took 16-17 s to healthy, and the first request
after a wake took 34-50 s in total (load + a 10-15k-token prefill with an image + thinking). One bug
found and fixed: `sheet.sh` failed on a single scene (ffmpeg `vstack` needs two inputs).

## Phase 3: the San Francisco 2060 film, hands-off, on DeepSeek Vision (2026-09-23 17:12-19:12)

The brief in one message; one interview question; answers "720p portrait, 12 scenes of 15 s, fast,
photoreal"; then untouched. The agent wrote and committed `stories/projects/13-san-francisco-2060.txt`
(12 scenes, seed 206001, style-only bible, every scene opening on its landmark, Maya described at
first mention in every scene), rendered scenes 1-3 with `until_scene 3`, reviewed the sheet,
continued, rendered 4-12, reviewed the three final sheets, wrote the logline, reported.

| measured | value |
|---|---|
| 720p portrait 15 s scene, clean GPU | **541-553 s** (one 609 s), against 936-1098 s the night before beside the stray 90 GB server |
| render, 12 scenes | 2 h 55 min wall including the pause |
| sleep/wake cycles | 2 renders: unload 17:16:36 → reload 17:44:21-17:44:42 (21 s); unload 17:45:40 → reload 19:09:04-19:09:26 (22 s) |
| model requests in the whole film | 11 chat completions; context ended at 27% of the 84k window, cache hits 99%; no compaction |
| judgment | pixel checks all correct and consistent with `precheck.py` (no border, mask, doubled face); semantic misses: the agent kept a suspended gondola for "a real cable car" (scene 3), and passed a Giza pyramid for "the Transamerica Pyramid" (scene 4) and Big Ben for "Coit Tower" (scene 5); it declared "no redos needed" |

### Retry of the review step after two fixes (19:13-19:50)

Fixes: the tools now print, beside each sheet, what each row was asked to show (text-vs-image per
row), and the prompt makes look-alike landmarks misses that must be described physically on redo.
The session was resumed with `rig/film-pi.sh -m vision -c` and given one nudge to redo the review step. The agent then called `review_scenes all`, wrote an asked/shows
verdict per scene, found exactly the three misses (3 gondola, 4 pyramid, 5 clock tower), rewrote
those scenes ("a real street cable car on steel rails ... an open-sided wooden car", "a tall white
tapering skyscraper with narrow windows and a pointed peak", "a plain white fluted concrete column
with no clock") with seeds 206002-206004, ran one `redo_scenes 3 4 5` (three scenes, 544-547 s
each, old takes in `redo-1/`), verified the new sheet, updated the logline and reported. Context
41% of 84k at the end, still no compaction; 3 h 20 min of rendering for the whole film.
Verified by eye afterwards: scenes 3 and 4 are right (an open wooden car on rails up the hill; a white tapering tower with the hologram); scene 5 still opens on a Big Ben clock face for its first frames before the fluted column appears, which the agent's report noted honestly and kept as the best of its one retake. Kinks left: the report named the
old-take folders `redo-3/4/5/` (they are `redo-1/`) and the logline's time of day was invented.

## 2026-09-23 20:40-20:47: /film and the ds4-serve lifecycle, tested for real (main session)

| test | result |
|---|---|
| `rig/tests/run.sh unit` (stub pi API, no GPU) | all assertions pass: /film on/off/status, director prompt appended once per turn, state restored from session entries, image warning, lifecycle by provider |
| real pi: `pi --offline --no-extensions -e rig/film-rig.ts --model local/vision --no-session -p "..."` | extension loads under jiti, hooks run, DeepSeek Vision answers via llama-swap; 27 s including load |
| `run.sh render swap` (model loaded in llama-swap) | tool unloads it, renders 2 x 5 s at 480p (44 s + 43 s), pre-checks + sheet, 113 s total; wired 5.4 GB after |
| `run.sh render ds4` (engine started with `model vision`) | `model stop` 1 s, render 92 s, `model vision` restart 8 s (page cache warm), engine serving again on :8000, pi catalog kept its `local` entries, 101 s total |
| `run.sh rpc` (real headless pi on local/vision) | `/film status` shows the preflight; `/film <brief>` turns director mode on, sends the brief, the model replies as the director with the interview line; `/film off` works; the model stays loaded in llama-swap afterwards (unload it) |
| `run.sh loop` (normal headless pi session, all extensions auto-loaded, local/vision, only `/film` typed) | the model itself called render_and_wait 35 s after the brief; llama-swap empty for the whole render (1m47s); reloaded 4 s after the tool returned; reviewed the sheet 50 s later with an asked/shows verdict per scene (both match); ALL OK |
| `model vision --yes` cold-ish start | 8 s to "listening" with the file in page cache; 92.6 GB wired while loaded |

Where the /film change lives in git: commit e5b221f (20:41, labelled "skills movie-prompt, scene-breakdown, cast") swept it in from
the working tree of another session; the rig commits before and after are labelled correctly.
