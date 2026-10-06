---
name: screenplay
description: Write the whole film as a shot-by-shot screenplay before any planning or rendering, so nothing is left to the video model - every shot's place, people, framing, the exact spoken line with its face cue and delivery, background action, light and sound - in the format this Mac's film rig renders well and with the craft that makes it land (a game, lines with a turn, background that answers the foreground, a set-up button). Use it whenever the user asks for a film with dialogue, a story, a sketch, a news report, an interview, a comedy, or says "write the script", "direct exactly what happens", "leave nothing up to the model"; the studio skill runs it before scene-breakdown, and scene-breakdown turns its shots into the project file.
---

# screenplay — the whole film on paper first

Write `stories/screenplays/<slug>.md`, the film's one creative document. Planning turns each shot into one project
line, word for word. Evidence: `rig/bench/screenplay/results.md`, from two rounds of blind judging. The examples below
are deliberately from other films. Never reuse them; find this film's own.

## How to work

A reply has room for 16,384 tokens, thinking included. Planning the whole film in your head runs out of room and
writes nothing; this was measured on two models. So think on paper:

1. **Notes first.** Write `stories/screenplays/<slug>-notes.md` with:
   - the premise;
   - the game, in one sentence: the contrast or pressure that repeats and escalates (for a drama, the want);
   - the shape: seconds / 8 = shots, plus the genre's spine;
   - every concrete thing the brief asks for, as a checklist.
2. **Brainstorm.** Add at least 25 rough candidate beats to the notes, one line each: who speaks, the exact line, and
   what happens around them. Then mark the best ~15 and their order. Measured: this method made screenplays funnier
   than format rules alone (judged "funny" 5-6 vs 2-3).
3. **Write the screenplay in the format below**, in two writes: the header, the cast and the first half of the shots,
   then the rest with `edit`.
4. **Run the checks below** and fix what they name. Don't add a "harsh editor" revision pass: it scored lower and
   broke the cue order.
5. **Keep thinking at the default level.**
   - Think Max wrote worse, and at the 16K cap it wrote nothing.
   - Thinking off narrated a plan and never wrote the file.

## The craft (what separated the best screenplays, per two blind judges)

- **Every line is a real person's grievance, affection or claim, with a turn in its last few words.** Examples:
  - a mourner: "She left me the house. And the eleven cats. Mostly the cats.";
  - a coach: "We lost by forty. I've never been prouder of a scoreboard."

  A line that only describes, or says the same thing twice, is dead. So is a line that explains the plot.
- **Distinct voices.** Every speaker sounds like who they are (age, job, mood).
  - Never give every speaker the same dialect, the same sentence template or the same cadence ("X. Y. Z."). The judges
    flagged all three as writer's tics.
- **What surrounds the line answers it; it doesn't depict it.** The background contradicts the line, quietly confirms
  it, or tops it.
  - Example: a mayor says "the flooding is under control" while a kayak drifts past the window behind her.
  - Showing exactly what was said was the weakest choice in every judged screenplay.
- **Background actions are simple and readable.** One clear action a small figure can do that reads on a phone. Skip
  multi-step business with props, crowds or animals.
- **Hold the conceit to the end.** If nobody notices, nobody ever notices: not the host, not the last speaker. A
  silent character never speaks.
  - Breaking this mid-film was the most common failure.
  - So was a spine out of order (a sign-off, then another interview).
- **Escalate, and end on a button.** The button is one image, usually silent, that the line just before it sets up.
  - Never show the button early. One screenplay gave its reveal away in shot 1.
  - An ending image that nothing set up is not a button.
- **Use the genre's spine and keep its order.** For example:
  - news: anchor, reporter, witnesses, official, sign-off, studio;
  - heist: plan, crew, job, twist, getaway.
- **Specifics of the real place and time:**
  - real streets and landmarks, described physically;
  - local gripes;
  - the season or holiday the user asked for, in every shot's dressing and a few lines (never a pun that explains
    itself).

## The rig's facts (so the screenplay renders)

- A shot is one continuous 8 s clip (5-6 s for a short beat). The video model renders each shot from that shot's text
  alone and never sees the others.
- So every shot describes in full:
  - the place, with landmarks described physically;
  - every person in frame: a name or role, an age and three fixed visual traits;
  - the framing and camera move;
  - the light;
  - a last "Sound: ..." sentence.
- Recurring characters have one fixed description in the cast list. Repeat its key traits in every shot they appear
  in: a judge marked down a shot that leaned on the cast list alone.
- **Speaking shots (interim 2026-10-03; what is measured and what is only a default:
  `docs/data/shot-lab/README.md`).**
  - **Who speaks is the real risk, not when.**
    - LTX ties the voice to a time, not a place (the LTX-2 report). Human raters found LTX-2.3's line in the right
      speaker's mouth in 24% of multi-speaker clips (MTAVG-Bench).
    - So: ONE speaker per shot, named right before the speech verb.
    - Others may be in the frame if each is described as silent, mouth closed ("Leo listens, silent, his mouth
      closed"). Clown Sighting's clown stood behind 17 speakers, and in 70 multi-face clips of earlier films no
      second face followed the voice.
    - The gate fails a shot where a second face mouths the line.
    - Two people speaking in one shot is untested: give each line its own shot.
  - **Framing: close-up to full length.**
    - In sync on the first take: medium close-up, waist up and knees up (shot lab, 7/7, confidence 10.5-11.4, faces
      180-490 px), and Warm's full-length takes (8/9, faces 115-180 px).
    - The sync meter (v3) checks any face of 32 px or more, so the old "medium close-up or close-up only" limit is gone.
    - Not yet measured: wide shots where the speaker's face is under about 100 px.
    - A shot with `[cast=...]` is composed at medium scale whatever the line asks. In the lab, "full length" and "wide
      from across the street" both came out waist-up. Don't count on `[cast]` for a wide speaking shot.
  - **Facing:** frontal or three-quarter is the default; profile is untested.
  - **Defaults, kept until the lab measures them** (the evidence is weak or confounded, but none goes against them):
    - nothing in front of the mouth (a microphone at the chest, below the chin);
    - no smile, grin or laugh while speaking;
    - no walking or leaning while speaking;
    - the line fills the shot at about 2 words a second: 10-16 words in 8 s, or a short shot for a short line.
  - **Always** (craft, and the lint enforces it):
    - before the speech verb, what the face does (eyes, brows, breath);
    - between the verb and the quote, the voice in under 15 words; the cue goes BEFORE the quote, never after it;
    - single quotes around the spoken words.
- On-screen text comes out garbled. Never make a joke depend on a sign, caption or map.
- Light goes on the place or the air, never on skin. The image model paints light words onto the body: in Thorns and
  Static (2026-10-03, seen once each) "a flicker of lightning on her cheek" became white lightning-bolt marks on both
  cheeks, and "the grey glow of the static on her cheek" a glittery patch of static. Write "lightning flickers in the
  sky behind her", "the screen's grey light fills the room".
- A `[still]` shot moves what its first frame shows. The image model draws the opening frame from the whole paragraph
  and the video model animates that picture, so put the shot's peak or threat in the opening sentences (seen once each,
  Thorns and Static):
  - shot 22's first still drew ordinary surf, and ordinary surf is what moved; once the wall of water full of pumpkins
    was written into the opening image, the surge came;
  - shot 6's first still drew the lightning bolt, and the bolt stayed locked on the pumpkin for six seconds. For an
    instant event (a strike, a slam, a burst), describe the moment just before it in the opening sentences.

## The format

```
# <Title>
<one paragraph: the premise, the game, and how it ends>

## Shape
<aspect, resolution, shot count and lengths, which shots get [quality]>

## Cast
- `<name>` — <who>: <age, build, face, hair, costume> (one line each; recurring characters only)

## Sound
<the film's ambience in one sentence>

## Shots
1. **<shot type>, <place>, <length>, <who>.** <one paragraph, the shot as the video model sees it: place; who is in frame
   and how big; the face cue; the speech verb; the delivery; 'the line'; anyone else in frame, silent, mouth closed, and their
   background action; the light; Sound: ...>
2. ...
```

## Checks before you hand it on (run them; count with bash, never in your head)

- `python3 rig/bench/screenplay/score.py stories/screenplays/<slug>.md`. It reports:
  - shots and total seconds;
  - spoken lines and how many sit in the 10-18-word band;
  - lint findings from the rig's dialogue lint (fix every one);
  - shots with more than one speaker;
  - whether the recurring background character is behind the speaker in every speaking shot;
  - theme and place coverage.
- Read your lines aloud in your head, one per shot. Is each one a line a real person would say, with a turn at the
  end? Does any shot explain the joke? Does anyone notice what they must not? Does the silent character
  speak?
- Every concrete request in the brief appears.
- No light words on skin. Every `[still]` shot's opening sentences show its threat already in frame, or the moment
  just before an instant event.

Then `scene-breakdown` (or the director's PLAN step) turns each numbered shot into one project line, keeping every
quoted line word for word.
