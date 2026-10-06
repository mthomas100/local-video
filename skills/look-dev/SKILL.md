---
name: look-dev
description: Brainstorm and lock the visual and sonic style of a video or film before it is planned — the vibe, palette, light, lens feel, era, wardrobe, weather, pacing, score — from presets and references, then render three 2-second look tests on this Mac so the user picks by eye. Use when the user talks about vibe, aesthetic, mood, style, "make it feel like", a genre, a director or film reference, a colour palette, or asks to brainstorm what would look cinematic; use before scene-breakdown, or on an existing film that "looks generic".
---

# look-dev — decide how it looks and sounds before deciding what happens

A style is a bundle of concrete choices the model can shoot: palette, light, camera
behaviour, lens feel (in safe words), production design, wardrobe, weather and time of day,
pacing, sound and score. "Cinematic" is not a choice; "one sodium lamp, teal shadows, a slow
push-in, rain on the glass" is. `references/aesthetics.md` is the menu.

## 1. Brainstorm (fast, with the user)

Offer three or four candidate vibes in one AskUserQuestion, each as a preset name plus one
sentence of concrete choices, mixing one safe pick, one bolder, one unexpected. Draw from
`references/aesthetics.md` presets and `movie-prompt/references/director-looks.md`. If the
user gave a reference (a film, a photographer, a music genre, an era), translate it into
the eight slots before offering. Let them combine or edit ("that, but at night").

## 2. Look tests (30 s of GPU each; run one at a time, never during another render)

For the two or three finalists, render a 2-second 480p clip of a neutral test subject
(a person at a window, or the film's real lead if `cast` has them) with ONLY the style
sentence plus one line of action:

    vidgen --no-open --seconds 2 --size 480p --seed 7 -o /tmp/look-A.mp4 "<location>. <lead sentence> turns from the window toward the camera. <style bundle as one paragraph, sound last>"

Then a strip for comparison: `ffmpeg -i /tmp/look-A.mp4 -vf "fps=2,scale=320:-1,tile=4x1" /tmp/look-A.png`
for each, look at them, and show the user the paths (or `open` them). Pick together.

## 3. Lock it as a look bible

Write `~/repos/local-video/stories/looks/<slug>.md` with: the eight slots filled in shootable
words, the exact style sentence to put at the END of every scene (no "film grain", no
"anamorphic", no format words), the sound and score line, the wardrobe palette per character,
and which look-test seed and clip it was chosen from. `scene-breakdown` uses it for BIBLE;
`movie-prompt` uses it for the style sentence. Commit as `local-video: look: <slug>`. Never put words that freeze
people in the style sentence ("stillness", "motionless", "frozen"). It goes into every speaking shot:
liminal-clowns' "uncanny stillness" did, and its dialogue sounded flat (2026-09-27).

## Don't

- Don't put the director's or film's name in a prompt; names do nothing, choices do.
- Don't test looks at 720p or longer than 2 s; the look reads at 2 s and 480p.
- Don't let a look bundle carry story content; that becomes a prologue in every scene.
