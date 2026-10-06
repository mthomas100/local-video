# Prompt rules for LTX-2.5 films, and the render that proved each one (2026-09-23)

The model is LTX-2.5 int8, distilled mode, on the ltx-2-mlx engine. Each rule below cost
at least one 15-second render to learn. The rejected takes are kept next to the finished
films under `~/Videos/vidgen/` as `*-draft{1,2,3}/` and `redo-N/` folders; look at a
contact sheet of one when a rule seems arbitrary.

## The start of the prompt is the first shot

The model stages whatever the prompt opens with. A shared paragraph prepended to every
scene became a prologue in every scene:

| leading text | what every scene opened with |
|---|---|
| style plus both leads described | a six-second static two-shot of both leads posing, even in scenes with one of them |
| style plus "the Firebird is a real glowing bird" | a crowd watching a flaming bird at a station |
| style only, ending "real adult actors ... people look at each other" | a crowd of extras looking at each other |
| the same style text, placed after the scene | the scene's own first sentence |

So `stories/story.sh` sends `"$scene $BIBLE"`, the bible holds only style, camera and
locale, and characters are described inside each scene. The ice-queen film of 2026-09-22
seemed immune only because its one character was in every scene anyway.

## One continuous shot per generation (2026-09-24)

The nyc-2000-slavic-neon film wrote two or three shots into each 15 s scene with "Cut to".
Every artifact of that film came after such a cut: letterbox bars in the second half of
scenes 3 and 5 (both takes of 3), a duplicated cat and a swapped lead in the retake of 3.
The shots before the cuts were clean. So each line of a project is now one camera setup
and one move, and the edit cuts between clips (`stories/story.sh` adds a short
audio fade at each cut). **Its length is a per-shot choice, not a fixed number**: `[secs=N]` anywhere in
**5-15 s** (nothing in the rig clamps it: `vidgen` renders what you ask, snapped to LTX's 8k+1 frames at 24 fps,
and 20 s is the model's cap per generation) — with `SECS=` only the default and 7-9 s the usual middle.
Use the whole range: 5-6 s for one object or one reaction (a diamond hitting marble, a hand freezing), 7-9 s for
a beat carrying dialogue (**never longer than 9 s with a line in it**: the dialogue rules were measured on 8 s
shots, and longer speaking shots are untested), 12 s for a moving wordless shot, 15 s once per film for a wordless
showpiece with `[quality]`.
Vary the durations as you vary the shot sizes: a film where every shot is the same length reads as mechanical.
A close-up that carries an emotion is its own line, and often the shortest one in the film.

## Landmarks: describe them physically, from the first draft

Named alone, famous places come out as look-alikes: a Giza pyramid for the Transamerica
Pyramid, Big Ben for Coit Tower, a gondola for a cable car (2026-09-23); a Gothic tower for
the Empire State Building, no billboards in Times Square, a straw hut for "the robot hut on
steel legs" (2026-09-24); a narrow red footbridge with round arches for the Golden Gate
Bridge and pink Georgian houses for the Painted Ladies (fast-mode A/B, 2026-09-24).
Described by shape, material, colour and surroundings, they came out right on the redo.
A look-alike is a miss, never "close enough".

## Scale by people or measures, never "as big as <an object>" (2026-09-25)

In halloween-clowns-sf, "a real giant pumpkin as big as a delivery van" drew a delivery van: a
pumpkin riding on a van (shot 1), pumpkin shells on car chassis beside a van (shot 3), a pickup
truck beside the pumpkin (shot 4), headlights under the pumpkin (shot 16). The object named for
scale gets staged. "Taller than the people beside it" gave the right giant pumpkin with no extra
object (shot 15). Use the people in the shot, or plain measures.

## A city is a landmark

"High above San Francisco at night" gave a generic dense city twice (shots 1 and 14 of the same
film), while every physically described landmark in it read (the Golden Gate twice, the Painted
Ladies' pastel row, Lombard's flower-bed curves). Describe the skyline the same way.

## Characters: describe in-scene, name them, fix three traits

"Ivan, a man of about thirty-five, tired kind eyes, dark stubble, grey parka," at first
mention in each scene kept Ivan recognisable across ten unanchored scenes with one seed.
An unnamed "metro driver in a grey parka" in one scene became a curly-haired stranger.
A vague "prince" was re-gendered (2026-09-22). Describing a character who is only referred
to (Mara, who left a note) put her in the room. Ages drift: a "man of about thirty" with
"curly dark hair" read fifty in every scene of one film; "a young man of about thirty"
helps, and consistency within a film matters more than the number.

## Keyframe-first: `[still]` on landmark shots and recurring-character shots (2026-09-26)

`[still]` makes `story.sh` draw the shot's first frame with Qwen-Image-2.1 (`bin/still`, from the
line itself with its dialogue removed, at the video's frame size) and animate it with `vidgen -i`.
The renders that decided it (`~/Videos/vidgen/rig-tests/iter3-0926/`, 9:16 portrait, the
halloween-clowns-sf lines and look; `rig/bench/char-keyframe.py`):

| test | text only | still first |
|---|---|---|
| Coit Tower, quality mode, 480p | a thin lighthouse-like tower by the bay, at dusk (as in halloween-clowns-sf shot 3, 720p) | the real tower: a thick fluted column with a ring of arched windows on a wooded hill, at night, the jack-o'-lantern at its foot, held through the move |
| Painted Ladies, quality mode, 480p | a pastel row on a slope, but in daylight with no neon | the gabled row at night, neon-lit, the skyline behind, rising over the row as asked |
| Marrow (one character sentence, seed 1031), lines 5, 13, 16 and two more seeds | five different men in fast mode and five in quality mode (the paint style alone stays) | one character in three compositions: the same paint design, ruff and bells, kept through each clip in fast mode |

The image model's stills were right in 3 of 3 seeds for both landmarks. One reference image of a
character conditioned at frame 0 or 96 (`--image plate IDX 0.2-0.4`, from LTX or from the image model)
carried the costume and paint into every clip but also its framing: from frame 0 the clip opened on the
plate (at 0.3-0.4 the line's giant pumpkin never appeared), from frame 96 it morphed into the plate at
the end. So a still per shot, drawn in that shot's own composition, and never one image for every shot.
Quality mode is no identity fix either: its five clips of Marrow were five men too.

Costs and caveats: about 50 s a still at 704x1104 and 1-1.5 min at 704x1280 (plus 15-20 s to load the
image model), at most about 46 GB, never beside a render. Image-to-video took the same time as
text-to-video (42-45 s for 5 s at 480p fast). The image model paints pseudo-text on neon signs even
when told "no text". The still is the opening frame, so the line's first sentences must describe a good
one; a clip may still wander from it (line 13's grin became a man stepping back into the street).
A redo with a new `[seed=N]` draws a new still (`still-N.key`); `redo.sh` keeps the old one with its take.

## The user's reference photos of places: `[place=<image>]` (2026-09-27)

The human gave five photos of liminal spaces (a hotel corridor, a tiled pool corridor, the backrooms, a cloud-painted
room, a dark mall escalator), 320-854 px tall. Measured:
- Qwen-Image-2.1 image-to-image never adds the asked people to the photo, at any strength from 0.15 to 0.75; at 0.6-0.75
  it redraws the room crisply and keeps it exactly. That is the clean-up `bin/still --place` does (strength 0.7).
- LTX-2.5 image-to-video straight from the photo (the hotel corridor, cropped to 9:16): the corridor held exactly for
  5 s and a family of four clowns with a red balloon walked in from the far end, as the line asked.
So `[place=...]` opens a shot on the real place and the line brings the people in. A close-up of a character in that
place needs the character in the first frame: `[place=...] [cast=...]` (below).

## Anchors (reference frames) hurt at 0.6

`bin/pick-face-frame` picks the largest sharp face, usually an extreme close-up. Anchored
at pixel frame 16 and strength 0.6, the next scene held that close-up for all 15 s
(vasilisa scene 6, first take) or moved its location to the reference (a cafe interior
became the forest). Unanchored scenes with in-scene descriptions and a fixed seed held
identity. `ANCHOR_STRENGTH=0` disables anchoring for a project; keep `[ref=N]` for a
deliberate match cut only.

## Locations: state them in the first words

"Inside the dark pawnshop at night, the lights just switched on, ..." was respected;
a scene whose text implied the shop (a ladder, the egg, the old man) played outdoors in
daylight. "Golden evening light in the flat's kitchen" once became a field at sunset when
the sentence started with the light rather than the room, so lead with the place.

## Realism words, and what drifts without them

- A cat-hero film under "shot on 35mm with anamorphic lenses" came out as a CGI cartoon
  cat. "Real documentary-style footage of a real domestic cat, a live-action short film
  shot with a real cinema camera" with a new seed came out photoreal, giant-cat scenes
  included. Animal leads and fantasy scale pull toward animation; say "real".
- "subtle film grain" in the bible drew a film-strip border with sprocket holes around
  every scene, twice, in two different films; removing the phrase removed the border.
- "40mm spherical lens" plus pet-camera content gave circular fisheye masks in three
  scenes. "ordinary 40mm lens, a clean rectangular full-frame image" fixed two of them;
  the third kept a soft rounded frame. Binocular and pillarbox masks appear for the same
  reason: any lens or format word is taken as a picture of that format.
- "real adult actors who resemble no celebrity, natural skin texture" reads as photoreal
  human film and never caused a problem when it sat after the scene.

## Ambiguous nouns, duplicates, crowds

- "fumbles the bow" in a scene that also said "violinist" produced a violin, not archery.
  Say "a wooden longbow" and "the arrow".
- Crowded action shots can double a character (two Lenas side by side, twice, at two
  seeds). "the only woman in the shop" plus a solo close-up ("Close-up on Lena's face
  alone") fixed it on the third take. Keep the number of people in a shot explicit.
- Extras are fine when the scene names them ("a heavy man of about forty in a football
  shirt"); the model only invents crowds when the prompt talks about people abstractly.

## Dialogue, cuts, sound, on-screen text

- Dialogue that matches the mouth (2026-09-27, measured with `rig/audit/lipsync.py`: the largest face's lip opening
  against the speech-band loudness, CPU only). In the out-of-sync shots of the last three films the line came last,
  after the ambience, was 2-4 words in an 8 s shot, and the face was asked to grin or smile; the mouth moved 330-500 ms
  BEFORE the voice (zero-lag correlation -0.57 to 0.1, in-sync shots 0.4-0.8). A/B, same clown and seeds, 720p
  portrait: old style corr 0.41/0.26 at -375/-500 ms; the line as the shot's action ("He looks straight into the lens
  and speaks slowly and clearly in a deep, tired voice: '...'", one speaker facing the camera, 20 words in 6 s, no
  grin) corr 0.42/0.59 at -83 ms. So: one visible speaker, facing the camera, the line right after who is in frame,
  about 2 words a second, nothing else for the mouth. The pre-check prints a `lipsync:` line per dialogue shot and
  flags `lipsync:off`; the stitch shifted a clip's audio when its mouth matched the voice at an offset (scene 8 of
  halloween-clowns-sf-portrait: -0.09 to 0.54 after a 417 ms shift).
  **DISPUTED 2026-09-27 12:14:** the human watched liminal-clowns, made with this rule, and found many dialogue shots
  out of sync, while this meter passed 9 of 10. The meter was never calibrated: on planted offsets its "in sync" rule
  passes 400 ms. So the rule above is a prompt habit, not proof of sync. The stitch shift is off by default
  (`LIPSYNC_NUDGE=1`). Open work, with root-cause candidates and fixes (audio-first `a2v`, a sync gate): `docs/dialogue-sync.md`.
  **SUPERSEDED 2026-10-04 (the shot lab, `docs/data/shot-lab/`):**
  - The 330-500 ms above does not reproduce on the calibrated meter: liminal-clowns' raw clips read 10/10 in sync. What
    viewers saw was the stitch's drift, now fixed.
  - 66 of 69 lab first takes were in sync across 35 kinds of shot.
  - The two real risks are WHO speaks and a speaking face under ~50-100 px.
  - Current rules: `rig/film-director.md` DIALOGUE. The shot menu: `dialogue-shots.md`.
  `precheck.py` transcribes each clip (Parakeet v3) when the render tools run it, so the
  review can compare what was said with what was asked.
- Performance (2026-09-27, *to test*): the human found the liminal-clowns delivery flat or awkward. All ten
  lines had one soft voice word and no other direction, and the bible said "uncanny stillness". Direct every line: a
  performance note in the plan, face and body cues before the speech verb, the voice after it, pauses as beats
  (`performance.md`). One definition of a spoken line for every parser: `rig/dialogue.py`.
- "Cut to" produces a real cut inside one generation, and the second half of such clips is
  where artifacts appear (above): cut in the edit instead. Distant faces are the model's
  weakest output for speech: a speaking face under ~50 px does not form the words (`dialogue-shots.md`).
- The last sentence is the sound: "Sound: ..." with the ambience and one specific sound; the film-wide ambience goes in
  the project's `SOUND=`. Never name a sound-making object in the BIBLE or in the picture part of a line: the bible's
  "a saxophone" was drawn as a player, a band and a lone instrument in four shots of halloween-clowns-sf-portrait
  (2026-09-26); `bin/still` drops "Sound:" sentences and story.sh gives `SOUND=` to the video model only.
  The engine's audio is near-silent and `vidgen` normalises it to -16 LUFS.
- Neon signs, notes and phone screens render approximate text (CAFE YAGA came out
  legible; NOVEMBER written in frost came out as a scribble). Write the word, do not
  rely on it.
- Thought bubbles requested as "a hand-drawn thought bubble floating above her head with
  an app icon in it" rendered as real drawn bubbles.

## Timings on the M5 Max 128 GB (fast mode, GPU alone)

| clip | measured | per second of film |
|---|---|---|
| 480p portrait 448x704, 15 s | 152-159 s (2026-09-24, clean GPU) | about 10 s |
| 720p portrait 704x1280, 15 s | 541-553 s (2026-09-23, clean GPU) | about 36 s |
| 720p landscape 1280x704, 8 s | 278-280 s (2026-09-24) | about 35 s |

The 16-18 min per 720p scene measured on 2026-09-22 had a stray 90 GB model server beside
the render. `--quality` (dev model with guidance, two stages): see the A/B note below.
Peak Metal memory at 720p portrait 15 s was 53 GB during decode. Add twenty percent for
redos; a typical film needed two to four redos out of eight to twelve clips.

## Process rules that cost the most

- One render at a time. No LLM on the GPU during a render. Check before starting.
- Stop a run only in its first three clips and only for a defect that repeats in every
  clip; after that, finish and redo single clips. Four early restarts on the first
  night were cheap (two or three scenes each); a late restart would have cost an hour.
- Same text plus same seed reproduces the same clip: a redo must change one of them.
- Keep every rejected take; a human reviewing in the morning wants to see why.
- One change per commit, `local-video: <what>`; the git log is the diary.
