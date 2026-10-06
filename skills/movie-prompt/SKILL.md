---
name: movie-prompt
description: Turn a rough idea, a scene note or a weak prompt into a vivid, model-ready cinematic prompt for this Mac's LTX-2.5 video rig (vidgen and film). Use whenever the user asks to enhance, punch up, make vivid, "give the treatment to", rewrite or direct a video or scene prompt, or says a result looked flat, generic, cartoonish or off-brief; also use it silently before rendering any scene you wrote yourself.
---

# movie-prompt — from idea to a prompt the model can shoot

The model reads a prompt like a director reads a shot description: full sentences, in order,
one flowing paragraph. "Cinematic" does nothing; a named camera move, a light source, a
physical action and a sound do everything. The rules below are the ones this rig paid for
(`~/repos/local-video/skills/film/references/prompt-rules.md`) plus the published LTX-2
guide; `references/` holds the vocabulary, the director looks and worked examples.

## Do this

1. Read what the user gave: a logline, a mood, a half-prompt, a complaint about a render.
   Decide the deliverable: one clip (up to 20 s, `vidgen`) or one shot of a film (a line in a
   project file). **A film shot's length is chosen per shot from the beat, 5-15 s** (`[secs=N]`;
   `SECS=` is only the default, 7-9 s the usual middle, and **never over 9 s if the shot carries
   dialogue**) — scale the detail and the word count to that length, never pad or trim a shot to fit
   an average. Do not ask questions for a first draft; write it, then offer
   two alternates that change one thing each (camera, or time of day, or the beat).
2. Write the prompt in this order, 40-110 words for a shot (count them with `wc -w`), present
   tense, one paragraph:
   1. **Location and time first** ("Inside a night tram depot in Riga, rain on the glass,").
      A famous place is described physically, never named alone ("the Golden Gate Bridge, a
      huge rust-red suspension bridge with two tall Art Deco towers of stacked rectangular
      portals").
   2. **Who**, at first mention, as an appositive with a name, an age and three fixed
      visual traits ("Mara, a woman of about thirty, cropped ash-blonde hair, freckles,
      a green rain jacket,"). Say "a real domestic cat", "an adult man". Never a bare
      "prince", "the bow", "people".
   3. **One clear action with a beginning and an end**, then the reaction. Emotion as a
      physical cue, never a label: "her jaw sets", not "she is angry".
   4. **Camera**: a shot size, one named move and its speed, and what it lands on ("slow
      push-in ending close on her hands"; "an aerial drone shot gliding low over the bridge").
      One continuous shot: no "cut to"; a close-up that matters is its own line in the film.
   5. **Light**: source, direction, colour ("one sodium lamp from the left, blue dusk
      behind").
   6. **Sound, last sentence**: "Sound: ..." with the ambience and one specific sound. Dialogue is NOT
      here: the spoken line as the shot's action right after who is in frame (one visible speaker facing the camera, about 2 words a second so it fills the shot, no grin, smile or laugh while speaking; see rig/film-director.md "DIALOGUE"), DIRECTED: the face and body before the speech verb, the voice in under 15 words after it, a pause written as a beat (`../film/references/performance.md`); a last "Sound: ..." sentence for the shot's own sound: `Mia, eyes red, pulls her coat tighter, looks at her father and says, small and unsteady, rising at the end: 'Are we still in the same building?'`
3. Style words go at the END (the model stages whatever comes first): "Real documentary-
   style live-action footage shot on a digital cinema camera with an ordinary 40mm lens, a
   clean rectangular full-frame image, shallow depth of field, natural skin texture, real
   adult actors who resemble no celebrity."
4. Run the checklist in `references/checklist.md` against the draft. Fix, then deliver the
   prompt in a fenced block, followed by one line on what you changed and why.

## Never

- Negative prompts (no input for them in fast mode), comma tag stacks, "masterpiece",
  "8k", "ultra detailed".
- "film grain" (draws a film-strip border), "anamorphic", "fisheye", "35mm" as a format
  (draw masks); "vertical 9:16" in the text (set it with `--portrait`).
- Describing a character who is only referred to (it puts them in the room), or more
  than three named people in one scene.
- Text the story depends on being legible; write the word, plan for a scribble.
- Distant faces for an emotional beat; go medium or close.

## Compounds with

`look-dev` decides the style bundle and the exact style sentence; `scene-breakdown` writes
the beats; this skill makes each beat shootable. `cast` supplies
the fixed character sentences to paste at first mention. `film` renders and reviews.
When the user wants a look ("like a Wes Anderson frame", "moody like Blade Runner"),
apply an overlay from `references/director-looks.md` as concrete camera/light/colour words,
never as the director's name (names do nothing).
