---
name: studio
description: Run the whole filmmaking chain on this Mac from one request — look, cast, scene plan, prompt polish, render, review, redo — with a dial for how many check-ins the user wants (hands-off, two check-ins, or step by step). Use when the user asks to "just make me a film/short/video about X" and wants the full treatment, or says studio, end to end, the whole pipeline, or "do all of it"; for a single planning or prompt task use the individual skill instead.
---

# studio — the whole chain from one sentence

The individual skills are the parts; this is the assembly line. Read each part's SKILL.md
as you reach its step (they are siblings in this folder), not all at the start: what you
read early is summarised away by the time you need it. This file decides the order, what
to ask once up front, and where to stop and show the user something.

**A local model in pi** (the film-rig tools `render_and_wait`, `review_scenes`, `redo_scenes`
exist): `/skill:studio` switches the rig's director mode on, which puts `rig/film-director.md`
in the system prompt. Its rules (one shot per clip, landmarks described physically, words
counted with bash, verdicts written while the sheet is visible, the honest report) outrank
anything summarised in your context. Render look tests and films only with those tools.

## 1. One up-front question set (a single AskUserQuestion, at most four questions)

Fill in whatever the request already said. Ask only what is open:

1. **Story**: logline, ending, tone. If they gave one line, offer to invent the rest.
2. **Shape**: film length, size and aspect from the `scene-breakdown` menu; quote render
   time. A film is a sequence of single shots cut in the edit. **Shot length is a per-shot
   creative choice, not a fixed average**: the screenplay sets each shot's seconds (`[secs=N]`
   on the line; `SECS=` is only the default) anywhere in **5-15 s** (nothing in the rig clamps it;
   20 s is the model's cap per generation) — and 7-9 s is just the
   usual middle. Keep a speaking shot at 9 s or under (the dialogue rules were measured on 8 s
   shots; longer speaking shots are untested); 12 s for a moving wordless shot; 15 s only for one wordless showpiece
   per film, with `[quality]`. Never pitch "N shots of 8 s" as the shape — pitch the total and
   say the shots run where the script needs them. Default: about 2 minutes
   (~16-20 shots, 7-8 s average), 720p landscape, fast, about 1.5 hours; 480p is about
   25 minutes for the same film. Quote time from the SUM of the per-shot seconds x the rate.
3. **Look**: three named vibes from `look-dev/references/aesthetics.md` presets, one
   safe, one bolder, one unexpected, each with its one-line bundle; or "photoreal
   documentary" (skip look tests); or "test them" (render three 2 s look tests first).
4. **Involvement**: *hands-off* (render everything, report at the end) · *two check-ins*
   (show the beat sheet before rendering, and the scene-3 contact sheet) · *step by step*
   (pause after look, cast, plan, and every review). Default: two check-ins.

## 2. The chain

0. **References** (when the user gives images, as paths or attachments): look at every one (`read` the file; you
   can see images), write down what each shows (the space, surfaces, colours, light, mood), and keep the paths:
   they feed the look bible, and each image becomes the `[place=<path>]` of the shots set there, so the film opens
   those shots on the real places (see `rig/film-director.md`). Images the user pasted into pi are saved under
   `stories/refs/<film>/`; `ls` it.
1. **Look** (`look-dev`): from their choice, write the look bible in `stories/looks/`. If
   they said "test them", render the 2 s look tests (with a local model: one small project
   through `render_and_wait`, then `review_scenes`), show the sheet (`open` it), lock the
   winner. Never during another render.
2. **Cast** (`cast`): reuse any character they named from `stories/characters/`; create the
   new leads (name, age, three traits) and write their files. Two to four leads. Each recurring
   character also gets one line in the project's `CAST=( "name|one sentence" )` and `[cast=name]` on the shots
   they appear in, so the rig draws one portrait and keeps one face (see `rig/film-director.md`).
3. **Screenplay** (`screenplay`): the whole film shot by shot in `stories/screenplays/<slug>.md`: every place,
   person, framing, exact line with its face cue and delivery, background action, light and sound, with the craft
   that makes it land, then its checks. If the user gave a screenplay, use it as is. Measured 2026-10-03: a full
   screenplay was rendered with every line in sync on the first take, no redo, no nudge
   (`rig/bench/screenplay/results.md`).
4. **Plan** (`scene-breakdown`): one project line per screenplay shot, every quoted line word for word; the
   continuity plan, the project file
   with the look's style sentence as the BIBLE and the cast sentences pasted at first
   mention. Famous places are described physically in every line that shows them. Every speaking shot gets a
   performance note and a directed line (`film/references/performance.md`); every speaking character a `voice:`
   and a `manner:` in their cast file.
   *Check-in 1*: show the beat sheet (one line per shot) and the estimate.
5. **Polish** (`movie-prompt`): run every scene through the checklist; fix silently,
   note anything the user should know (a line of dialogue you invented, text on screen).
6. **Render** (`film` steps 2-4): preflight the GPU, start the queue, wait with a
   background `until` loop, never poll with an LLM on the GPU.
7. **Review** (`film` steps 5-6): contact sheet at shot 3 (*check-in 2*: show it, and stop
   only for a defect that will repeat) and at the end; an asked/shows line per shot; a
   pre-check REDO is a redo; redo misses, at most three takes each.
8. **Report** (`film` step 7): final path and length, one line per shot with its verdict,
   take and pre-check result as printed, what was redone and why, what still misses, what
   could not be checked, measured timing. Update `IDEAS.md`, commit.

## 3. Rules that override the dial

- Even hands-off stops for a repeating defect in the first three scenes; restarting after
  that costs an hour.
- Never two renders at once; never an LLM on the GPU during a render; check first.
- One change per commit, `local-video: <what>`; the git log is the diary.
- If the user paints a look with a director's or film's name, translate it to choices;
  the name never goes in a prompt.
