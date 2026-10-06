# Prompt checklist (tick every line before rendering)

- [ ] One continuous shot: one camera setup, one move, no "cut to" (the edit cuts between
      clips; cuts inside one generation drew letterbox bars and duplicates on 2026-09-24).
- [ ] First words are the location and time of day.
- [ ] Every famous place or object is described physically (shape, material, colour, what
      is around it), never by name alone: the model draws look-alikes (Big Ben for Coit
      Tower, a Giza pyramid for the Transamerica Pyramid, a footbridge for the Golden Gate).
      A city is a landmark too: describe its skyline, not "high above San Francisco".
- [ ] Every person or animal is named (or given a fixed role) at first mention with age +
      three fixed traits, and "real" / "adult" are there where the model tends to drift
      (animals, creatures, giant props, fantasy scale; children never). Scale against
      the people in the shot or plain measures ("taller than the people beside it"), never "as big as
      <an object>" (it draws the object: "as big as a delivery van" put a van in four shots, 2026-09-25).
- [ ] Exactly one main action with a start and an end; reactions are physical cues.
- [ ] One named camera move with a speed and a landing point; a named shot size.
- [ ] A light source with a direction and a colour.
- [ ] Last sentence is sound: ambience and one specific sound, never the dialogue (2026-09-27: a line placed last,
      after the ambience, was a mark of the out-of-sync shots; the spoken line is the shot's action, right after who
      is in frame).
- [ ] A speaking shot is directed (`../../film/references/performance.md`): face and body cues before the speech verb,
      a voice cue of under 15 words after it, the feeling shown and heard, never named; a pause written as a beat;
      every quoted part starts with a speech verb; quote marks only around spoken words; no smile while speaking.
- [ ] Style sentence sits at the very end, contains no grain/lens/format trap words.
- [ ] Nothing negative, no tag stacks, no emotion labels, no ambiguous nouns.
- [ ] 40-110 words for a 5-10 s shot, up to ~150 for a 12-15 s film shot (a single `vidgen` clip may run to
      20 s and take ~200), counted for its OWN `[secs=N]` and never padded to an average,
      COUNTED WITH BASH (`wc -w`, or the awk line in rig/film-director.md), never in your
      head. Too long: cut adjectives from the action, camera or light; never cut a
      character's or a landmark's description.
- [ ] The shot's `[secs=N]` is the beat's length, not the film's average, and is inside 5-15 s; a shot
      carrying a spoken line is 9 s or under (the dialogue rules were measured on 8 s shots).
- [ ] The number of people in frame is explicit ("the only woman in the shop").
