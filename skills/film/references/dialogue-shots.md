# Dialogue shots: what the rig measured, and how to write each one (2026-10-04)

Measured in the shot lab (`docs/data/shot-lab/`: `summary.md`, `README.md`). Then pi wrote and
directed its own scene from this page ("The Last Car", phase C): six kinds of speaking shot, 8 of 8 in sync on the
first take with the gate enforced. Sources:
- the same speaker and line throughout, first takes only, 2 seeds per condition;
- sync meter v3, which reads planted offsets on mouths down to ~18 px;
- plus 28 lines from three films.

**The voice was in sync on the first take in every shot below, except where the speaker's face was small.** The two
real risks are WHO speaks and HOW SMALL the speaking face is. Framing, angle, movement, props and acting are not.

## The shot menu (portrait 704x1280 unless noted; "2/2" = both seeds in sync)

| shot | sync | how to write it |
|---|---|---|
| close-up, medium close-up, waist up, knees up | 2/2 each | as usual |
| full length, the person filling at least about half the frame | 2/2, plus films (82 px face in sync) | as usual |
| landscape waist up, landscape full length | 2/2 each | in landscape keep the speaker knees-up or closer for a sure line |
| a two-shot, one speaks | 2/2 | the speaker named before the verb; the other "silent, mouth closed". A pronoun with two men in the shot gave the king's line to the minister (the iteration-9 film, shot 3, 2026-10-04; the gate passed it), so the lint refuses it |
| over the shoulder | 2/2 | the listener's back or shoulder in the foreground, silent |
| a group of four, one speaks | 2/2 (one take doubled a character) | say how many people and name each; keep groups small |
| two people trading lines in ONE shot | 2/2 lab, 1/1 pi's film (each line from its own face) | the speaker's name before EVERY speech verb: "Dana says, ...: '...' Then Leo answers, ...: '...'"; "she says" also worked when only one woman was in the frame, but write the name when two people share a pronoun |
| profile (it came out at 60-75 degrees) | 2/2 | "in profile, talking to X off to the left" |
| walk-and-talk toward the camera, or beside a dolly | 2/2 each | "as she walks, ... she says" |
| an orbiting camera | 2/2 | "the camera slowly circles her as she says" |
| a mic at the mouth, a coffee sip before the line | 2/2 each | props are fine; the line after the sip |
| laughing, shouting, whispering through the line | 2/2 each | direct the voice freely |
| speech from frame 0; 3 words in 8 s; 29 words in 8 s | 2/2 each | timing is free; about 2 words a second still reads best |
| a painted clown face | 2/2 | as usual |

## Where it fails: small speakers

| speaker's face at the line | portrait framing that gives it | first takes in sync |
|---|---|---|
| 100 px or more | a person at least about 2/3 of the frame's height, or closer | all (dozens) |
| 50-100 px | a person about 1/3 to 2/3 of the frame's height | 2 of 3 |
| under 50 px | a person a quarter of the frame or smaller | 0 of 2 (the mouth does not form the words) |

- **A small speaker walks in.** LTX brings a speaker drawn small to the lens to deliver the line. A wide still of
  Dana far down the street became a medium close-up by mid-shot in 6 of 6 takes, and "she stays planted, the
  camera locked off" did not stop it.
- **To keep a speaker small, add `[hold]`.** It gives the shot's first frame again near the end, and it held the
  framing in 8 of 8 takes. Keep the face at about 100 px or more: about 1/3 of the frame's height and up.
- **To put a recurring character into a wide shot, use `[cast=x] [layout]`.** It draws the composition first, then
  puts the cast in. Without `[layout]`, `[cast]` draws the character at the portrait's scale whatever the line says.
- **For a line that must come from a distant figure, use `[offscreen]`.** The voice plays over the wide shot, the
  speaker turned away or out of frame, and the gate skips it.

## The gate (meter v3) checks
- **PASS:** the speaker's mouth follows the line (confidence 4.2 or more, offset within -125..+45 ms) and the words
  are heard.
- **UNMEASURABLE:** the face is under 32 px or hidden for more than half the line.
- **M9:** a second face mouths a one-person line.
- **M10:** one face speaks lines written for two people.
- **On a FAIL:** the rig retakes with new seeds (3 takes). Then fix the line: a closer framing, or the names before
  the verbs, or `[offscreen]`.
