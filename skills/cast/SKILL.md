---
name: cast
description: Create, look up and reuse recurring characters for this Mac's video rig so the same people, animals and looks can star across clips and films. Use when the user names a character they want again ("the ice queen", "Biscuit the cat", "Mara"), asks to design a character, wants a character bible, or when scene-breakdown and movie-prompt need the fixed description sentence for someone.
---

# cast — one sentence per character, reused verbatim

Identity across independent generations comes from words plus a fixed seed, and it held
across ten scenes when every scene repeated the same appositive at first mention. It did not
hold for a painted clown (2026-09-26: five different men from one sentence, in fast and in
quality mode): put `[still]` on the character's shots, so an image model draws each opening
frame from the same sentence and the video model animates it; that kept one face, paint and
costume across three compositions. One reference image for every shot imposes its own framing. So a
character is a file with that sentence, the seed the character was born under, the film
they came from, and a reference frame for the human to recognise them.

Store: `~/repos/local-video/stories/characters/<slug>.md`

```
# Mara
sentence: Mara, a woman of about thirty, cropped ash-blonde hair, freckles, a green rain jacket,
species/role: human, marine biologist
seed: 51            # the film seed she first appeared under; reuse it for the closest match
first film: the-frog-bride-of-riga (scene 2)
reference: ~/Videos/vidgen/the-frog-bride-of-riga/ref-from-2.png
voice: a low, dry alto, unhurried, faint Baltic accent; short sentences, deflects with a question
manner: stands square, hands in pockets; looks away before she admits anything
notes: freckles disappear at 480p in wide shots; keep her medium or close
```

## Do this

- **Create**: ask for or invent a name, an age ("a woman of about thirty"), and exactly
  three visual traits that survive a wide shot (hair colour and cut, one garment with a
  colour, one mark or accessory). Add "a real domestic cat" style realism words for
  animals. Write the file. Never a celebrity likeness; if the user names one, translate to
  traits ("a tall man with a grey beard and a black coat").
- **Reuse**: paste the sentence verbatim at first mention in every scene; keep the same
  seed as the character's film when identity matters more than novelty. Do not add new
  traits mid-film. If the human says "she looks different", the fix is more specific
  traits, not a longer list.
- **Voice and manner** (2026-09-27): give every speaking character a `voice:` (timbre and pitch, pace, accent, how
  they talk) and a `manner:` (how they hold themselves, a habit under stress). Scene lines and a TTS voice draw on
  them (`../film/references/performance.md`). Never paste either into `CAST=` or a first-frame prompt: the image
  model draws what it reads.
- **Update**: after a film, if `bin/pick-face-frame` produced a clean face, record it as
  `reference:` and note which scenes drifted, so the next writer knows the risks.
- **List**: `ls ~/repos/local-video/stories/characters/` and read the first line of each.

Commit character files with `local-video: cast: <name>`.
