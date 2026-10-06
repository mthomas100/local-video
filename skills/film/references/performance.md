# Directing the performance: how a line should sound, and what the face and body do (2026-09-27)

**Status: written from LTX's own prompting guides, other audio-video models' guides and ordinary directing craft;
not yet measured on this rig.** Iteration 5 tests it (`docs/dialogue-sync.md`). Where a rule here
is marked *to test*, treat it as the default until a measurement says otherwise, and record what you saw.

Why this exists: on 2026-09-27 the human said the liminal-clowns dialogue flat or awkward.
Every one of its ten lines had one soft voice word ("in a low voice", "in a quiet voice", "in a small voice", "in a
tired voice") and no other direction. Beyond "faces the camera" there was no face or body cue, no pause, and no change
inside the line. The look bible added "uncanny stillness" to every shot. The lines stated the plot ("Every room is the
same room. I keep losing the way."). The model delivered exactly that: flat, even, uniform.

## 1. Decide the performance before you write the line (the performance note)

A director never tells an actor "be sad". That is result direction, and it produces a generic face. The video model
is the same: it cannot play a label. For every spoken line, write a **performance note in the plan** (the beat
sheet), never in the prompt:

- **the moment before:** what just happened, and the body's state (cold, exhausted, out of breath, holding the child's hand);
- **the want:** what the speaker wants from the listener right now (to be believed, to calm her, to stop the argument);
- **the playable verb (the tactic):** to reassure, warn, plead, tease, deflect, confess, rally, dismiss, bargain;
- **the subtext:** what they mean and don't say;
- **the beat:** the feeling at the start and at the end. At most one shift in a 5-10 s shot (a
  longer wordless shot of 12-15 s may carry two), and at most two short
  sentences on either side of it;
- **the operative word:** the one word the line hangs on.

Then compile the note into what a camera and a microphone can record (§2). The note is also how you keep the film's
emotional arc straight (§4).

## 2. Compile the note into the prompt: seen, then heard, then the reaction

Order inside the shot's line, within the 40-110 words (the rest of the line as in `prompt-rules.md`):

```
[place] [who: the fixed character sentence] [the moment before: face and body, seen] [one small action or gaze
shift] and says, [the voice: under 15 words]: '[the words]' [a beat, then the second part, if any] [the reaction
after: breath, gaze, stillness, a small smile]. [camera] [light] Sound: [the shot's own sound].
```

- **Face** (before the speech verb; the first-frame still keeps it, so the clip *starts* in the emotion): eyes (wet,
  narrowed, searching, unfocused, steady), brows (pinched together, raised, drawn down), gaze (drops, finds the
  listener, glances away and back), breath (a shaky breath, a slow exhale through the nose), jaw (tight, a swallow).
- **Body** (before the speech verb): posture (shoulders dropped, leaning in, straightening), **one** small gesture
  that lands on the operative word (a hand on the child's shoulder, fingers tightening on the balloon string), or
  stillness as a choice ("holds perfectly still").
- **Voice** (after the speech verb and before the quote; the image prompt drops it automatically, see §6): pitch (low,
  high, rising), pace (slow, clipped, rushing, drawing out each word), volume (a whisper, a murmur, raised), texture
  (rough, breathy, cracking, steady, warm), and **where it changes** ("slowing on the last words", "breaking on the
  word home").
- **Pauses are beats**, written as actions (LTX's guide: "she pauses", "a beat of silence"): end the first quote, add
  `She pauses, looks down the corridor, then says, softer:` and a second quote. **Every quoted part starts with a
  speech verb** (says, asks, whispers …), so the pre-check hears both parts and the first frame drops both.
- **Quote marks only around spoken words.** Write "breaking on the word home", never "breaking on 'home'": the rig's
  parsers treat every quoted span as dialogue.

**Feeling → cue vocabulary.** The feeling is for your planning; only the cues go in the prompt:

| feeling (never written) | face | body | voice |
|---|---|---|---|
| weary | half-lidded eyes, a slow blink, gaze drops | shoulders sag, leans on the wall | low, slow, trailing off, a sigh before the words |
| frightened, held in | eyes wide and darting, brows raised and drawn together | stiff, hands pressed together | quick, breathy, thin, catching on one word |
| tender | soft eyes, a small nod | leans closer, a hand on a shoulder | warm, low, unhurried, nearly a whisper |
| defiant | chin up, a steady unblinking gaze | squares the shoulders | firm, clipped, even, leaning on the operative word |
| grief, held back | eyes glistening, brows pinched upward, jaw tight | very still, a swallow | quiet and steady, then breaking on one word |
| hopeful | eyes lift, brows rise | straightens, turns toward the light | brightening, quickening, rising at the end |
| suspicious | eyes narrow, a sideways glance | head tilts, weight back | slow, flat, measured, a pause before the key word |
| playful (a child) | bright eyes, brows up | bounces on her heels, tugs the string | high, quick, sing-song |

**Keep the mouth for the words** (lip sync): no smiling, grinning, laughing or crying mouth *while* speaking. Put the
feeling in the eyes, brows, breath, posture and voice. A smile or a trembling lip can come *after* the line, as the
reaction. *To test:* this rule came from the uncalibrated 2026-09-27 meter.

**Keep the head still for the words** (measured 2026-09-27, iteration 5 A/B, rig/sync gate): "his eyes flick down to
the water and back up ... he leans in" made the model push Pip's face into the lens, top-down, the mouth hidden under
the nose, in both seeds (UNMEASURABLE, then conf 2.1). The same method with cues only in the eyes, brows and breath
("her eyes lift to the balloon ... her brows rise"; "eyes wide, brows raised and drawn together") passed the gate in
4 of 4 takes and lifted the voice's arousal out of the neutral band. Lean, bow, look down or step toward the lens only
in a shot without a line.

**Reduce competing action while speaking:** a gaze shift or one small gesture, not walking or handling an object.
Liminal-clowns shots 2, 10 and 19 spoke while trying a door, touching a pillar and stepping onto an escalator. LTX's
own guide says to reduce competing visual activity where lip sync matters.

**Worked example.** Liminal-clowns shot 3 as rendered: `... She faces the camera and says, in a quiet voice: 'We
have to keep walking, Pip. The light's still on at the end.'` Directed (note: want = get Pip moving again; verb =
to rally; subtext = she is scared too; beat = firm → gentle; operative word = keep):

```
On the hotel corridor, warm beige walls, a close-up on Moth's face alone, a woman of about thirty-five, slim, white
face paint, a round red nose, a patched teal-and-cream costume with a silver bell collar. Her eyes are tired but
steady, brows drawn together; she takes a slow breath, faces the camera, her eyes on Pip just beside the lens, and
says, low and firm, leaning on the word keep: 'We have to keep walking, Pip.' She pauses, glances down the corridor,
then says, softer: 'The light's still on at the end.' Warm ceiling light behind her. Sound: a soft bell, a carpet hush.
```

(104 words. Its first-frame prompt, from `bin/still`: "... Her eyes are tired but steady, brows drawn together; she takes
a slow breath, faces the camera, her eyes on Pip just beside the lens, and speaks. She pauses, glances down the
corridor, then speaks." The pre-check's asked lines: both quoted parts. Checked 2026-09-27.)

## 3. Write lines people would say

- Subtext over statement. People rarely name their feelings or narrate the plot, and a line that explains is what
  sounds awkward.
- Spoken phrasing: contractions, fragments, a question, an unfinished thought. Let a line answer the previous
  speaker's, so the film is one conversation.
- Each character speaks their own way. The `cast` file's `voice:` holds the timbre and pitch, pace, accent and habits
  (Pip short and dry; Moth practical and warm; Sprout asks questions).
- The line fills the shot at about 2 words a second, *including* the pauses you wrote. A beat of about 1 s costs 2
  words.

## 4. Across the film: an emotional arc, not one note

- In the plan, give each character's arc in one line and place each dialogue shot's beat on it. Sketch the film's
  energy curve: a quiet film still needs variety inside the quiet (a whisper that cracks, a child's sudden brightness,
  a flash of anger swallowed).
- No two consecutive lines with the same delivery. If the look is "subdued", vary pace, pitch and texture, not only
  volume.
- The look bible must never freeze people: no "stillness", "motionless" or "frozen" on shots that speak.
  Liminal-clowns' "uncanny stillness" went into every dialogue prompt.

## 5. Eyeline and framing (*to test*)

Iteration 4 made speakers face the camera, which helps a sync meter see the mouth. An actor talking into the lens
reads as addressing the viewer, like a presenter or a vlog, and that can feel awkward in a drama. Cinema's default is
three-quarter, with the eyeline to the listener just off the lens. Until iteration 5 measures both, keep the face
frontal to three-quarter with the mouth fully visible, and name who they speak to ("her eyes on Pip just beside the
lens"). A close-up or medium close-up carries a performance; a wide shot does not.

## 6. What the rig does with each part

One definition of a spoken line, shared by all of these: `rig/dialogue.py` (a speech verb, up to 100 characters of
delivery direction without quote marks, then the quoted words).
- `bin/still` (the first frame) keeps the face and body cues and drops the voice cue plus the quoted words: `says,
  <up to 100 characters>: '...'` becomes `speaks.` So write the voice cue in under 100 characters, after the speech
  verb, before the quote.
- The pre-check lists every quoted span as asked dialogue and compares it with the transcript.
- **Audio-first (*to test* in iteration 5):** the same note becomes a TTS instruction. Qwen3-TTS 1.7B takes a
  natural-language `instruct` for emotion and prosody; it is local (`~/.pi/agent/skills/tts`, `~/repos/Qwen3-TTS`,
  `~/repos/mlx-audio`). Give it the character's fixed voice plus this line's delivery ("a tired man in his forties, a
  low rough voice, slow; frustration rises on the word twice, then flat and defeated"). The `a2v` video prompt then
  carries only the face and body cues.

## Sources

LTX prompting guide (docs.ltx.io, open-source model, usage guides: "express emotion through physical cues, not
abstract labels"; write beats as "she pauses", "a beat of silence"; voice qualities; whisper, mutter, shout, scream).
The awesome-ltx2 prompt guide ("The woman's face crumples; she takes a shaky breath"). The Maestro LTX-2 embedded-audio
LLM guide (pair each line with visible acting cues; avoid long monologues without acting beats; reduce competing
activity where lip sync matters). Google's Veo 3.1 prompting guide ("He looks up at the woman and says in a weary
voice, ..."). The Qwen3-TTS model card and blog (instruction-controlled emotion and prosody). Judith Weston,
*Directing Actors* (1996): playable verbs and objectives over result direction.
