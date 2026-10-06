---
name: film
description: Make a multi-scene short film (1 to 7 minutes, with synchronized audio and dialogue) on this Mac with the LTX-2.5 model, by interviewing the user about the story, length, size, aspect ratio and quality, then writing a scene-by-scene project file, rendering it unattended, reviewing every scene from contact sheets, and re-rendering the scenes that missed. Use this skill whenever the user asks for a film, a short, a story, a movie, an episode, a music video, a sequence of scenes, or "another one like the cat film", and whenever a request for "a video" describes more than one shot or more than 20 seconds; for a single clip under 20 seconds use the vidgen skill instead.
---

# film — a short film from a brief, on this Mac

`vidgen` renders one clip of up to 20 s. A film is N such clips ("scenes", 15 s each by
default) written as one project file, rendered back to back by `stories/story.sh`, and
stitched with ffmpeg. This skill is the process that made nine films on 2026-09-23; the
rules in it were each paid for with a wasted render, so read `references/prompt-rules.md`
before writing scenes. Repo: `~/repos/local-video`. Output: `~/Videos/vidgen/<NAME>/<NAME>.mp4`.

## 0. If you are a local model in pi with the film rig loaded

When the tools `render_and_wait`, `review_scenes` and `redo_scenes` exist in your session (the
`film-rig` extension in `~/.pi/agent/extensions`), you are the local orchestrator and the GPU
must alternate between you and the renderer. Use those tools instead of the commands in steps
4 to 6 below: `render_and_wait` unloads you, renders, and returns the log, the pre-check
verdicts and the contact sheet when it is done; `review_scenes` makes a sheet without rendering;
`redo_scenes` re-renders only the named scenes. The full loop for that mode, with the sheet
checklist, the landmark rule and the report rules, is `rig/film-director.md`; director mode puts
it in your system prompt (`/film`, `/skill:film` and `/skill:studio` turn the mode on;
`rig/film-pi.sh` starts a session already set up this way), so you do not need to read it or
`rig/film-rig.ts`. You need a vision model: `local/vision-q4-400k` (DeepSeek Flash Vision through
llama-swap) or `local/qwen27-262k`. The render tools return text; `review_scenes` shows the sheets
once, so write your verdicts in the reply that receives them.

## 1. Interview the user first

Sibling skills: `scene-breakdown` runs this interview and writes the beat sheet and project
file; `movie-prompt` polishes any scene or clip prompt; `cast` keeps recurring characters'
fixed sentences. Use them when the user asks for planning or prompt work without a render.

Ask before writing anything, with one AskUserQuestion call of up to four questions, so the
user is not surprised by an hour of GPU time spent on the wrong shape. Fill in whatever
their message already answered; ask only what is open. Recommended defaults first.

- **Story** (only if the message did not give one): who, what happens, how it ends, the
  tone. Offer to invent the rest. A logline plus an ending is enough.
- **Length**: 1 minute (~8 shots at a 7-8 s average), 2 minutes (~16 shots), 3 minutes (~24 shots).
  A film is a sequence of single shots cut in the edit. **Each shot's length is decided per shot by the
  screenplay, never as one fixed number for the film**: give each line `[secs=N]` anywhere in **5-15 s**.
  Nothing in the rig clamps it: `vidgen` renders what you ask, snapped to LTX's 8k+1 frames at 24 fps, and
  20 s is the model's cap per generation. How to use the range:
  5-6 s for an insert of a single object or one reaction, 7-9 s for a beat carrying a line (**keep a
  speaking shot at 9 s or under**: the dialogue rules were measured on 8 s shots, and longer speaking shots
  are untested), 12 s for a moving wordless shot, 15 s for one wordless showpiece per film with `[quality]`.
  A film whose shots are all the same length reads as mechanical; vary them, and quote the render time from
  the sum of the per-shot seconds.
- **Size and aspect**: 480p landscape 704x448 (drafts, long films; about 10 s of render per
  second of film), 720p landscape 1280x704 (cinematic finals; about 35 s per second: an 8 s
  shot about 4.6 min, measured 2026-09-24), portrait 9:16 of either (`PORTRAIT=1`, same
  cost). Quote the total: seconds of film x that rate, plus 20 percent for redos.
- **Quality**: fast/distilled (recommended; all measured times are fast) or `--quality`
  (about five times slower, sharper motion). Style: photoreal live action (default),
  or something else they name (animation, stop motion, a period look).
- Anything they insist on: character names and looks, lines of dialogue, a specific
  ending image, a title card, no dialogue, music.

Then confirm the plan in two lines (N scenes, size, mode, estimated finish time) and go.
Do not ask again mid-render; make the routine calls yourself and note them in the report.

## 2. Preflight (the GPU is a shared, single-tenant resource)

    pgrep -f "ltx-2-mlx generat[e]"          # must print nothing: one render at a time
    curl -s 127.0.0.1:8090/running           # local LLM must be idle; unload with /unload
    pgrep -x ds4-server; pgrep -x llama-server   # a model server outside llama-swap still holds the GPU
    vm_stat | grep 'wired'                   # over ~40 GB wired before the render starts means something big is loaded
    df -h ~ | tail -1                   # a scene is 3-25 MB; not a concern
    tail -3 ~/repos/local-video/logs/queue.log

Two renders at once swap and run five times slower each; an LLM loaded beside a render
slows its refine steps nine times. An idle DeepSeek server (`ds4-server`, launched by hand or
by the `com.example.ds4-server` launchd job) keeps about 90 GB wired even while
answering nothing; on 2026-09-23 one sat unnoticed through a whole night of renders, cost
8 GB of swap and stretched 720p scenes to 16-18 min. Stop it with `kill -TERM` (never -9,
Metal memory can leak) and `launchctl bootout gui/$(id -u)/com.example.ds4-server`
if the job keeps relaunching it; re-enable later with `launchctl bootstrap`. If the user might paste a command themselves, either
run it or hand it to them, never both.

## 3. Write the project file

Copy `references/project-template.txt` to `stories/projects/NN-<slug>.txt` (next free
number) and fill it. It is zsh: `NAME SIZE SECS SEED PORTRAIT MODE ANCHOR_STRENGTH`,
`BIBLE='...'`, `SCENES=( "..." "..." )`, one SHOT per line in double quotes (the runner and
the tools call them scenes: `scene-N.mp4`). Choose a fresh SEED (any integer not used by a
sibling project). Rules that matter most, with the reasons in `references/prompt-rules.md`:

0. **One continuous shot per line, no "cut to" inside a line.** The edit cuts.
   Its length is yours per shot (`[secs=N]`, 5-15 s, `SECS=` only the default): the beat
   decides, not the average — but keep a speaking shot at 9 s or under. On 2026-09-24 every letterbox bar and
   doubled character came after a cut inside one generation. **Famous places are described physically** in every
   line that shows them; named alone, the model draws a look-alike.

1. **The bible is style only** and the runner appends it after the scene text. Anything
   concrete in it (a character, a creature, "people look at each other") gets staged as a
   prologue in every scene. No "film grain" in it: that draws a film-strip border.
2. **Describe each character in every scene where they appear, at first mention**, as an
   appositive with a name, an age and three fixed visual traits: "Ivan, a man of about
   thirty-five, tired kind eyes, dark stubble, grey parka,". Identity across scenes comes
   from these words plus the fixed seed; it held across ten scenes without anchors.
   Do not describe a character who is only referred to (a photo, a note): describing them
   puts them in the room.
3. **Open every scene with its location** ("Inside the dark pawnshop at night, ..."); an
   implied location is not respected.
4. `[noanchor]` on every scene and `ANCHOR_STRENGTH=0`; reference anchoring froze scenes
   on the previous close-up. Use `[ref=N]` only for a deliberate match cut.
5. 40-110 words per shot for a 5-10 s shot (up to ~150 for a 12-15 s shot), counted with bash (`wc -w`),
   never in your head; present tense:
   who and what happens, then the shot size and camera move (push-in, slow orbit, tracking
   alongside, aerial drone glide), then light, then the sound in the last sentence. Dialogue (voiced and lip-synced): the spoken line as the shot's action right after who is in frame (one visible speaker facing the camera, about 2 words a second so it fills the shot, no grin, smile or laugh while speaking; see rig/film-director.md "DIALOGUE"), directed like an actor's line, with face and body before the speech verb and the voice after it (`references/performance.md`); a last "Sound: ..." sentence for the shot's own sound. To shorten, cut adjectives
   from action, camera or light, never a character's or a landmark's description.
6. Say "real", "a real domestic cat", "documentary-style", "real adult actors who resemble
   no celebrity", "ordinary 40mm lens, clean rectangular full-frame image". Animal leads
   and fantasy scale drift to CGI without "real"; lens words drift to fisheye masks.
7. No ambiguous nouns ("the bow" next to a violinist became a violin bow), no negatives
   (they do not work in fast mode), no vague nouns for people ("a prince" was re-gendered).
8. Text on screen is approximate; write it, never depend on it being legible.

Then `zsh -n` the file, source it in a subshell to count scenes, and commit it
(`local-video: <what>`, one change per commit, with the Co-Authored-By line).

## 4. Render, unattended

    cd ~/repos/local-video
    nohup zsh stories/run-queue.sh stories/projects/NN-<slug>.txt >/dev/null 2>&1 & disown

Progress: `logs/queue.log` and `logs/story-<NAME>.log`. Never poll with an LLM on the
GPU; wait with a background `until` loop on the scene files, e.g. until `scene-3.mp4`
exists, then until `(OK|FAILED) <NAME>` appears in `queue.log`. A scene FAILED is usually
a Metal OOM from something else on the GPU or a bad reference; fix and rerun the same
command, finished scenes are skipped.

## 5. Review at scene 3 and at the end

Contact sheets cost CPU only, so make them during the render:

    zsh ~/repos/local-video/skills/film/scripts/sheet.sh <NAME> 1 2 3 > /dev/null   # writes sheet-1-2-3.png in the film folder

Look at the sheet. Check, per scene: the scene opens on its own first sentence (no
prologue, no border, no circular mask); it is photoreal if asked; the right people and
animals, once each (no duplicated character, no re-gendered or aged-away lead); the
named location; the story beat is visible; the last frame of the film lands the emotion.
Stop the queue only in the first three scenes and only for a defect that will repeat in
every scene (a prologue, a border, cartoon drift): `pkill -f "run-queue[.]sh"; pkill -f
"story[.]sh"; pkill -f "ltx-2-mlx generat[e]"`, park the folder as `<NAME>-draft1/`, fix
the cause, restart. After that, finish the film and redo single scenes.

## 6. Redo what missed, at most three takes per shot

    zsh stories/redo.sh stories/projects/NN-<slug>.txt 5 7     # old takes kept in redo-N/

`redo.sh` renders only the named scenes (`ONLY=`), even on an unfinished film. Same text
and same seed reproduce the same clip, so change the text (name the missing lead, describe
the landmark physically, reword the ambiguous noun) or add a `[seed=N]` token to that
line. Do not spend an hour on one shot; note it in the report and move on.

## 7. Log and report

`bin/catalog` runs after every film. Add one logline to `stories/projects/IDEAS.md`
marked made, commit. Report: the final path and length; one line per scene saying what
it shows; which scenes were redone and why; what the user should look at (text on
screen, an actor's age, a mask); and the timing measured, so the next estimate is better.
Open Finder on the folder if the user asked to see it: `open ~/Videos/vidgen/<NAME>`.
