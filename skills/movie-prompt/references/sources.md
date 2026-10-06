# Where these rules come from (so you can check them)

Measured on this machine (highest trust; each cost a render):
- `~/repos/local-video/skills/film/references/prompt-rules.md` — 2026-09-23, nine films.
  Style-after-scene, in-scene character appositives, location-first, no anchors, "real"
  wording, no "film grain", no lens/format words, ambiguous nouns, duplicates, dialogue.
- `~/repos/local-video/README.md` timing table and `logs/runs.tsv` — every run.
- `~/Videos/vidgen/*-draft*/` and `redo-N/` — the rejected takes, with contact sheets.

Published guidance the vocabulary and ordering follow:
- LTX-2 official prompting guide, mirrored at
  https://github.com/wildminder/awesome-ltx2/blob/main/guides/LTX2-prompt-guide.md —
  order (shot, scene, action, characters, camera, audio), 4-8 sentences, one paragraph,
  present tense, dialogue in quotes, emotion as physical cues, avoid text/logos, avoid
  fast non-linear motion and scene overload.
- LTX-2.5 community guide https://ltx23.org/blog/ltx-2-5-prompt-guide — "Shot 1 ... cut to
  Shot 2" multi-shot syntax, 2-4 shots per generation, consistency clause.
- Cross-model guides (Seedance/Veo/Kling), e.g.
  https://www.atlabs.ai/blog/100-cinematic-camera-prompts-you-can-copy-2026 and
  https://www.seedance.tv/blog/seedance-2-5-prompt-guide — "name a real camera move, its
  speed and what it lands on"; five-part formula (camera move + speed + subject and framing
  + environment + look). Their tag stacks and negative prompts are NOT adopted: this rig's
  fast mode has no negative input, and tag words ("8k", "masterpiece") did nothing here.
- Third-party Claude skills reviewed and mined for structure, not installed (their lens
  and grain vocabulary conflicts with the measured rules):
  https://github.com/wuwangzhang1216/DirectorSKILL (director overlays, shot lists),
  https://github.com/jnMetaCode/ai-shortfilm-prompts (beat maps, invariant clauses),
  https://github.com/OSideMedia/higgsfield-ai-prompt-skill (Seedance-specific).

When a rule here disagrees with a published guide, the measured rule wins on this rig.
