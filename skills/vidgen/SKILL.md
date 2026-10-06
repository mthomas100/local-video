---
name: vidgen
description: Generate video (with synchronized audio) from a text prompt or a still image, entirely on this Mac, using the LTX-2.5 model through the `vidgen` command. Use when the user asks to make, render, animate, extend or redo a video clip locally, or describes a scene they want to see as video.
---

# vidgen — local text/image-to-video on this Mac

Everything runs through one command, `vidgen` (on PATH; source in
`~/repos/local-video/bin/vidgen`, handoff doc in `~/repos/local-video/README.md`).
It drives the LTX-2.5 int8 pack in `~/models` with the pure-MLX engine in
`~/repos/ltx-2-mlx`. Nothing leaves the machine.

## Do this

1. Turn the user's request into one concrete prompt (see "Writing prompts").
   Do not ask clarifying questions for a first draft; make a clip, then iterate.
2. Run it with the bash tool. A clip takes minutes, so use a long timeout
   (`timeout: 900000`) or run it in the background and report when done.

        vidgen "a heavy wooden door creaks slowly open, dust in a shaft of light"
        vidgen -i /path/to/photo.jpg "the camera slowly pushes in as the trees sway"
        vidgen --seconds 8 --size 720p --seed 7 "..."       # fixed length; default lets the model choose
        vidgen --quality "..."                              # dev model + CFG: better, ~5x slower
        vidgen --portrait "..."                             # 9:16
        vidgen extend --video ~/Videos/vidgen/X.mp4 --seconds 2 "and then it slams shut"
        vidgen retake --video ~/Videos/vidgen/X.mp4 --start 1 --end 3 "a cat walks through"
        vidgen --dry-run "..."                              # print the engine command only

3. Report the output path (`~/Videos/vidgen/<stamp>-<slug>.mp4`), the wall
   time it printed, and the seed from the sidecar `.json` so the user can
   reproduce or vary it. `vidgen` opens the clip in QuickTime when run from a
   terminal; from an agent pass `--no-open` and tell the user the path.

## Writing prompts

LTX-2.5 wants one flowing paragraph, present tense, 30-80 words: subject and
action first, then camera (slow push-in, handheld, static wide shot),
lighting and mood, and finally the sound (dialogue in quotes, ambience,
music). Describe motion rather than a list of adjectives; it predicts the
clip length from the action you describe. Avoid negatives ("no people"),
they do not work.

## Modes and costs (M5 Max 128 GB, measured 2026-09-22; table in the README)

- fast 480p 5 s: about 1 min. fast 720p 5 s: about 3 min. quality 480p 5 s: about 4.5 min.

- default (`--fast`): distilled pipeline, no CFG. Use for drafts and most clips.
- `--quality`: dev model with CFG, two-stage. Sharper motion and prompt
  adherence, roughly five times the time (measured: 272 s vs 56 s for 5 s at 480p).
- `--hq`: second-order sampler. Only for a final render.

## Don'ts

- Do not run two generations at once; one already uses most of the GPU.
- Do not run an LLM on the GPU during a render. Memory would allow Qwen 27B
  (~25 GB) beside a render, but measured 2026-09-23: Qwen loading + one vision
  prompt during a 480p render slowed the render's refine steps from ~20 s to
  180 s each, and Qwen did not answer in 4 min. An agent driving this loop must
  only call the LLM between renders. Check `curl -s 127.0.0.1:8090/running`;
  unload with `curl 127.0.0.1:8090/unload` before starting a render.
- Do not edit `~/repos/ltx-2-mlx`; it is an upstream clone, `git pull` it.
