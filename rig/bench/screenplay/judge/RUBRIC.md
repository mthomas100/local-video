# Blind judging rubric for the screenplay eval (2026-10-03)

You are judging several screenplays written for the same brief (below). They are labelled with letters only; you
are not told who or what wrote them. Read every one in full before scoring.

The brief (paraphrased): a ~3-minute vertical (TikTok) local nightly-news report from San Francisco, a
reporter interviewing people about a clown sighting; each witness describes what the clown did, while in the
background the clown is always doing something absurd that nobody notices; a newsroom; absurd, humorous, good
dialogue, a cohesive narrative; direct exactly what happens in every shot and leave nothing to the model;
a Halloween vibe wherever possible.

Score each screenplay 1-10 on each criterion (10 = professional comedy-writer quality):

1. **Funny**: would a viewer laugh? Specific, surprising jokes; the background gags pay off against the
   foreground lines (contradict, illustrate, one-up); escalation; a strong ending button. Generic or explained jokes
   score low.
2. **Dialogue**: lines sound like real people on the evening news (distinct voices, sincere, deadpan), each line
   short enough to say in one 8-second shot, none that recite the plot.
3. **Cohesion**: a clear news-broadcast spine (anchor, reporter, witnesses, official, sign-off), an arc that
   builds, and an ending that lands.
4. **Brief fidelity**: news report, reporter, witnesses, clown always in the background and unnoticed, San
   Francisco, a newsroom, Halloween throughout, about 3 minutes.
5. **Directability**: could a video model render each shot from its paragraph alone? Concrete places, people
   described with fixed traits in every shot, one speaker per speaking shot, framing, light, sound, background
   action stated.

Then give:
- an overall rank (best first);
- for each screenplay, the single best moment and the single weakest moment, quoted briefly;
- two sentences on what most separates the best from the rest.

Output a JSON block first: `{"scores": {"A": {"funny": n, "dialogue": n, "cohesion": n, "fidelity": n,
"directability": n}, ...}, "rank": ["X", ...]}`, then the notes.
