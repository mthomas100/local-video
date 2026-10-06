---
name: scene-breakdown
description: Interview the user about a video idea (length, format, resolution, aspect ratio, scene count, quality, style, cast, ending) and break the idea into a numbered scene list with a story arc, per-scene beats, camera plan and continuity plan, written as a project file ready for the film skill to render. Use when the user has an idea for a movie, short, episode or multi-scene video and wants it planned, storyboarded, split into scenes, or turned into a shot list; use it before movie-prompt polishes the scenes and before film renders them.
---

# scene-breakdown — from an idea to a scene list the rig can shoot

**When a screenplay exists** (`stories/screenplays/<slug>.md`, from the `screenplay` skill or the user), it is the
source: one project line per numbered shot, in order, every quoted line word for word, every detail kept. Add only the
rig's tokens and each recurring character's description, and skip the interview questions it already answers.

Output: `~/repos/local-video/stories/projects/NN-<slug>.txt` (the next free number), in the
`film` skill's format, plus a short beat sheet the user can react to before any GPU time is
spent. Facts about the rig that shape every answer: each line of the project is ONE
continuous shot (one generation; the edit cuts between them, so no "Cut to" inside
a line: the 2026-09-24 film's letterbox and duplicate artifacts all followed one). **Each shot's length is set
per shot from the beat, anywhere in 5-15 s** (nothing in the rig clamps it, and 20 s is the model's cap; `SECS=` is
only the default, 7-9 s the usual middle, and a speaking shot never longer than 9 s) — so
quote cost from the sum of the per-shot seconds; rendering
costs about 35 s per second of film at 720p and about 10 s at 480p in fast mode, three
times that in quality mode; dialogue works when one visible speaker says a line that fills the shot (about 2 words a second) as the shot's action; faces must stay medium or
close; famous places must be described physically or the model draws a look-alike.

## 1. Questionnaire (one AskUserQuestion call, at most four questions; skip what the message answered)

- **Story**: logline + how it ends + the tone (funny / romantic / eerie / bittersweet).
  Offer to invent whatever is missing. Ask for any must-haves: names, a line, an image.
- **Length**: 1 min (~8 shots at a 7-8 s average), 2 min (~16), 3 min (~24). Say out loud that the
  shots are not all the same length: the screenplay sets each one, 5-15 s.
  Quote the render time for each at the size they pick (seconds of film x 35 s at 720p,
  x 10 s at 480p, plus 20% for redos).
- **Format**: landscape 16:9 (cinematic, aerials, panoramas) or portrait 9:16; 480p
  (drafts, long films) or 720p (finals, showpieces). Fast or `--quality`.
- **Style**: photoreal live action (default), a look bible from `stories/looks/` (made by
  the `look-dev` skill; offer to run it if the user talks about vibe), or a director look
  (`movie-prompt/references/director-looks.md`).

Confirm in two lines: N scenes, size, mode, finish time. Then plan.

## 2. Arc first, then beats, then shots

Fit the story to a shape before writing shots; the model shoots moments, not plots.
- 4 beats: setup · complication · turn · ending image.
- 8: hook · world · want · obstacle · attempt · reversal · climax · ending image.
- 12+: add a midpoint gift or loss, a second obstacle, a quiet beat before the climax,
  and a coda that rhymes with the opening (same place, changed person).
Each beat is one to three SHOTS with a visible change (a decision, a discovery, a
reversal, a touch): for example an aerial establishing shot, a medium shot of the action,
a close-up of the reaction. Each shot is one line of the project: one camera setup, one
move. **Length is chosen per shot from the beat** (`[secs=N]`, 5-15 s: 5-6 s for an insert or one
reaction, 7-9 s for a beat with a line and never longer with dialogue, 12 s for a moving wordless shot, 15 s once
in the film for a wordless showpiece) — vary the durations as you vary the shot sizes. Vary shot sizes line to line (extreme wide or drone, wide, medium, close-up,
extreme close-up on a detail). The last frame of the film is the image the audience keeps;
write it first, then work backwards.

**Dialogue: direct it like a director** (`~/repos/local-video/skills/film/references/performance.md`, 2026-09-27;
the human found flat, one-note lines flat or awkward). Give each speaking character an arc in one line. Give
every speaking shot a **performance note** in the beat sheet: the moment before, the want, the playable verb
(reassure, warn, plead, tease, deflect …), the subtext, the beat (the feeling at the start and at the end), and the
operative word. Then write a line people would actually say: subtext over statement, contractions, answering the last
speaker, never the plot explained. No two consecutive lines get the same delivery. In the project line, the note
becomes face and body cues before the speech verb and a voice cue after it (`movie-prompt`).

## 3. Continuity plan (this is where films fall apart)

- Cast: two or three recurring characters, each with a name, an age and three fixed
  visual traits, pasted verbatim at first mention in every scene (`cast` skill). No
  unnamed recurring people. Extras are named singly ("a heavy man in a football shirt").
- Locations: three to five, each introduced in the first words of its scene, varied
  deliberately (interior night, exterior day, a landscape, a vehicle, a crowd).
- Shot variety: no two consecutive shots share a shot size or the same face. Alternate:
  aerial, wide, insert of an object, over-the-shoulder, a hand, a close-up.
- Landmarks: every shot that shows a famous place describes it physically (shape,
  material, colour, what is around it), never by name alone.
- Time: state time of day in every shot; move it forward.
- One fixed SEED for the film; `[noanchor]` on every line; `[ref=N]` only for a match cut.
- `[still]` on every shot of a named landmark and of a recurring character: the rig draws the first
  frame with an image model (the real landmark, the same face every time) and animates it
  (`skills/film/references/prompt-rules.md`, keyframe-first).
- Props that carry meaning (a ring, a feather, a jam jar) are described the same way each
  time; on-screen text is never load-bearing.

## 4. Write the project file

Copy `~/repos/local-video/skills/film/references/project-template.txt`, fill NAME, SIZE,
SECS (the fallback only — put `[secs=N]` on every shot whose beat is not the average, 5-15 s), SEED (fresh), PORTRAIT, MODE, a
style-only BIBLE, and one line per shot. Each line follows the `movie-prompt` order:
location and time → who (appositives) → one action → camera → light → sound last (a speaking shot:
who → face and body → says, the voice: 'the words' → the reaction → camera → light → sound). Run
every line through `movie-prompt/references/checklist.md` and count words with bash
(`awk -F'"' '/^"/{n++; print "shot "n": "split($2,a," ")" words"}' <file>`), never in your
head. `zsh -n` the file; commit (`local-video: <what>`).

## 5. Hand off

Show the user the beat sheet (one line per shot: number, location, beat, shot size and move) and
the render estimate; offer to start `film` now. Add a logline to
`stories/projects/IDEAS.md`. Do not render from this skill.
