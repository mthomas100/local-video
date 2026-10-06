# Before and after (from the 2026-09-22/23 renders)

## A clip that already worked (keep this shape)
"A weathered lighthouse keeper in a yellow raincoat stands on a rocky shore at dusk as huge
waves crash against the cliffs below, spray catching the last orange light; slow cinematic
dolly-in, dramatic storm clouds; roaring surf, wind, and distant gulls." → cinema-grade, first
try, 5 s 720p. Why: place + one figure + one action + a named move + light + sound.

## Rough note → shootable shots (one line per shot since 2026-09-24)
Before: "queen bored by gifts, prince does magic trick, she laughs, they kiss"
After, shot 1 (medium two-shot, 8 s): "Inside a great hall carved from ice at dusk, one
crystal chandelier, frost-covered flowers. Vasilisa, a woman of about thirty, pale, very long
platinum hair, a silver crystal gown, sits on a throne as Ivan, an adult man of about
thirty-five in a tall top hat and blue coat, sweeps the hat off and lifts out a white dove.
Slow push-in on the two of them; cold blue window light with warm candle fill. A dove's
wingbeats, a soft murmur."
Shot 2 (close-up, 6 s): "Inside the ice hall at dusk, close-up on Vasilisa, a woman of about
thirty, pale, very long platinum hair, a silver crystal gown: her composure cracks and she
laughs before she means to. Static camera, cold blue window light on her face. Her surprised
laugh." Both end with the style sentence: "Real documentary-style live-action footage,
ordinary 40mm lens, clean rectangular full-frame image, natural skin texture, real adult
actors who resemble no celebrity." (Before 2026-09-24 this was one 15 s scene with "Cut to";
the cut inside one generation is where letterbox bars and doubled people appeared.)

## A landmark, described so it cannot become a look-alike
Named only: "the Painted Ladies on Steiner Street" → generic pink Georgian houses (fast mode,
2026-09-24 A/B). Described: "the Painted Ladies, a row of tall narrow wooden Victorian houses
with steep pointed gables and bay windows, painted pastel blue, pink and yellow, on a steep
grassy hill with downtown skyscrapers behind".

## A prompt that drifted, and the fix
- "shot on 35mm with anamorphic lenses ... an orange tabby" → CGI cartoon cat.
  Fix: "real documentary-style footage of a real domestic cat, a live-action short film shot
  with a real cinema camera". Photoreal, giant-cat dreams included.
- "subtle film grain" anywhere → a film-strip border with sprocket holes. Fix: delete it.
- "a second prince in red and gold pushes a chest of gold" → a woman in a red dress.
  Fix: "a second adult man, a bearded prince in a red and gold doublet".
- "fumbles the bow" beside "violinist" → a violin bow. Fix: "a wooden longbow".
- Scene text that implied the shop → played outdoors. Fix: open with "Inside the dark
  pawnshop at night,".

## The user's fashion prompts (long, tag-heavy) still worked as single showpiece clips
because they are one location, one figure, one mood, and the model tolerates ~300 words for
a 15 s clip. The negative-prompt blocks were dropped (no input for them) and "vertical 9:16"
was set with `--portrait` rather than text.
