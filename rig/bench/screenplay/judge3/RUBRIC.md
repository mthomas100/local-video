# Blind judging rubric for the screenplay eval (2026-10-03)

You are judging five screenplays written for the same brief (below). They are labelled with letters only; you
are not told who or what wrote them. Read every one in full before scoring.

The brief (paraphrased): a ~2-minute vertical HD video, a nature documentary with a serious, hushed British narrator, about a tech startup office in San Francisco during Halloween week; the narrator whispers about the employees as if they were animals in the wild (the migration to the snack kitchen, the alpha engineer, the mating rituals at the costume contest); the employees also talk to camera in little interviews, totally serious about their jobs, but it is absurd; lots of dialogue, really funny, a good cohesive story, ending on some kind of twist; "direct exactly what happens in every shot, leave nothing up to the model".

Score each screenplay 1-10 on each criterion (10 = professional comedy-writer quality):

1. **Funny**: would a viewer laugh? Specific, surprising jokes; the background gags pay off against the
   foreground lines (contradict, illustrate, one-up); escalation; a strong ending button. Generic or explained jokes
   score low.
2. **Dialogue**: lines sound like real people on the evening news (distinct voices, sincere, deadpan), each line
   short enough to say in one 8-second shot, none that recite the plot.
3. **Cohesion**: a clear news-broadcast spine (anchor, reporter, witnesses, official, sign-off), an arc that
   builds, and an ending that lands.
4. **Brief fidelity**: a nature-documentary parody with a hushed narrator, a San Francisco startup office, Halloween
   week, employee interviews, the wildlife conceit (snack-kitchen migration, alpha engineer, costume-contest rituals),
   a twist ending, about 2 minutes.
5. **Directability**: could a video model render each shot from its paragraph alone? Concrete places, people
   described with fixed traits in every shot, one speaker per speaking shot, framing, light, sound, background
   action stated.

Then give:
- an overall rank (best first);
- for each screenplay, the single best moment and the single weakest moment, quoted briefly;
- two sentences on what most separates the best from the rest.

Output a JSON block first: `{"scores": {"A": {"funny": n, "dialogue": n, "cohesion": n, "fidelity": n,
"directability": n}, ...}, "rank": ["X", ...]}`, then the notes.
