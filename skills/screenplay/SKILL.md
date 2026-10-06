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
5. **Which model.** On this rig, Qwen3.8 Flash Next (`qwen38`) writes the best screenplays: blind-judged 76-82
   with this skill, 0 lint findings.
   - DeepSeek V4 Flash Vision (the director's model) at the 16,384-token reply cap failed 4 of 10 screenplay runs,
     spending a whole reply thinking and writing nothing, and its finished ones scored 48-66.
   - If you are the DeepSeek director, keep each reply small (one write per step).
6. **Keep thinking at the default level.**
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

- **A shot is one continuous take, and its length is a storytelling choice you make per shot**, written as the
  `<length>` in that shot's bold header (the plan turns it into `[secs=N]`). Keep it within **5-15 s** (nothing in
  the rig clamps it, and 20 s is the model's cap per generation);
  7-9 s is the usual middle, and **a shot carrying dialogue must stay at 9 s or under** (the dialogue rules were
  measured on 8 s shots; longer speaking shots are untested). Use the range: 5-6 s for one object or one
  reaction (a diamond striking marble, a hand freezing), 7-9 s for a beat carrying a line, 12 s for a moving
  wordless shot, 15 s once in the film for a wordless showpiece — the performance the audience should sit inside
  (a dance, a flute solo, a slow walk, a kiss). A screenplay whose shots are all the same length reads as
  mechanical; vary the durations the way you vary the shot sizes, and give the film's key beat its own long
  take. The video model renders each shot from that shot's text alone and never sees the others.
- So every shot describes in full:
  - the place, with landmarks described physically;
  - every person in frame: a name or role, an age and three fixed visual traits;
  - the framing and camera move;
  - the light;
  - a last "Sound: ..." sentence.
- Recurring characters have one fixed description in the cast list. Repeat its key traits in every shot they appear
  in: a judge marked down a shot that leaned on the cast list alone.
- **Speaking shots** (measured 2026-10-04 in the shot lab, 66 of 69 first takes in sync across 35 kinds of shot;
  the menu, with how to write each shot, is `skills/film/references/dialogue-shots.md`):
  - **Any framing, angle, movement, prop or acting.** All of these stayed in sync:
    - close-up to full length; over the shoulder; profile;
    - a walk-and-talk; an orbiting camera;
    - a mic at the mouth; laughing, shouting, whispering;
    - speech from the first frame.
    So write the shot the scene wants.
  - **WHO speaks.**
    - Put the speaker's name right before every speech verb ("Dana says", "Then Leo answers").
    - Write everyone else in the frame as silent, mouth closed.
    - Two people may trade lines in one shot when each line is named.
  - **HOW SMALL.** Keep a speaking face at about 100 px or more: a person at least about 2/3 of a portrait frame's
    height, knees up or closer in landscape.
    - Under 50 px the mouth stops forming the words.
    - A speaker drawn small walks to the lens unless the shot has `[hold]`.
    - For a line from a distant figure, write it off-screen.
  - **Always** (craft, and the lint enforces it):
    - before the speech verb, what the face does (eyes, brows, breath);
    - between the verb and the quote, the voice in under 15 words; the cue goes BEFORE the quote, never after it;
    - single quotes around the spoken words; about 2 words a second reads best.
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

- `python3 rig/bench/screenplay/score.py stories/screenplays/<slug>.md`, plus `--bg <name>` only if YOUR film has a
  recurring background character and `--theme <word|word>` only if the user asked for a theme. The checker serves
  your film: never add a character, theme or place to satisfy it (a model once added a silent clown to every shot
  of a nature documentary because an old checker counted clowns). It reports:
  - shots and total seconds;
  - spoken lines and how many sit in the 10-18-word band;
  - lint findings from the rig's dialogue lint (fix every one);
  - shots with more than one speaker (allowed only when each line is named before its speech verb; the gate fails one
    face speaking two named people's lines);
  - with `--bg`: whether that character is behind the speaker in every speaking shot;
  - with `--theme`: how many shots carry the theme.
- Read your lines aloud in your head, one per shot. Is each one a line a real person would say, with a turn at the
  end? Does any shot explain the joke? Does anyone notice what they must not? Does the silent character
  speak?
- Every concrete request in the brief appears.
- No light words on skin. Every `[still]` shot's opening sentences show its threat already in frame, or the moment
  just before an instant event.

Then `scene-breakdown` (or the director's PLAN step) turns each numbered shot into one project line, keeping every
quoted line word for word.
