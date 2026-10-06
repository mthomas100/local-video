#!/usr/bin/env python3
"""make_lab.py — writes the shot lab's project files (2026-10-03).

One factor at a time around a control: the same place, the same plain-faced speaker (Dana), the same 14-word line,
the same two seeds; only the shot changes. The lines follow the rig's writing conventions (place first, who is in
the frame, a face cue before the speech verb, a voice cue, a "Sound:" sentence) but deliberately break the old
framing rules where a condition tests them. Output: lab-portrait.txt, lab-landscape.txt, lab-portrait-2.txt here;
pi copies them to stories/projects/ and renders them.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEEDS = (4101, 4102)
PLACE = ("On a quiet residential street in San Francisco at dusk: a row of narrow pastel Victorian houses with bay "
         "windows and steep front stoops, a streetlight just flickering on, a few parked cars.")
DANA = ("Dana, a woman of about forty, short dark curly hair, a mustard-yellow raincoat over a grey sweater, small "
        "gold hoop earrings")
LEO = "Leo, a man of about sixty, a short white beard, a navy peacoat, a grey flat cap"
LINE = "'I counted every streetlight on this block twice, and three of them are missing.'"
SAYS = "says, puzzled and precise, slowing on the word three:"
CUE = "Her brows drawn together, her eyes on the lens, she"
LIGHT = "Soft blue dusk light, the streetlight's warm glow on her face."
SOUND = "Sound: a quiet street, distant traffic, a dog barking far away."
ALONE = f"{DANA}, the only person in the shot,"

def single(shot: str, cue: str = CUE, says: str = SAYS, line: str = LINE, extra: str = "") -> str:
    return f"{PLACE} {shot} {extra}{cue} {says} {line} {LIGHT} {SOUND}".replace("  ", " ")

CONDITIONS = {
    # id: (tokens, text) -- the control and the framing ladder
    "C0": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera, her face large in "
                                 "the upper half of the frame. The camera holds still.")),
    "F1": ("[cast=dana]", single(f"A medium shot from the waist up on {ALONE} standing on the sidewalk facing the "
                                 "camera. The camera holds still.")),
    "F2": ("[cast=dana]", single(f"A medium-wide shot from the knees up on {ALONE} standing on the sidewalk facing the "
                                 "camera, the houses behind her. The camera holds still.")),
    "F3": ("[cast=dana]", single(f"A full-length shot: {ALONE} stands on the sidewalk facing the camera, her whole body "
                                 "in the frame from her head to her shoes, filling about half of the frame's height, "
                                 "the pastel houses behind her. The camera holds still.")),
    "F4": ("[cast=dana]", single(f"A wide shot from across the street: {ALONE} stands small on the far sidewalk in "
                                 "front of the pastel houses, about a quarter of the frame's height, facing the camera. "
                                 "The camera holds still.")),
    "F5": ("[cast=dana]", single(f"An extreme wide shot from far down the street: {ALONE} is a tiny figure on the "
                                 "sidewalk, about one eighth of the frame's height, facing the camera, the long row of "
                                 "houses and the empty street around her. The camera holds still.")),
    # people in the frame
    "P1": ("[cast=dana,leo]", f"{PLACE} A medium two-shot from the waist up: {DANA}, and {LEO}, stand side by side on "
           "the sidewalk facing the camera, Dana on the left, Leo on the right, the only two people in the shot. Dana is "
           "the only one who speaks; Leo listens with his mouth closed, silent, and nods once only after she finishes. "
           f"The camera holds still. Her brows drawn together, her eyes on the lens, Dana {SAYS} {LINE} {LIGHT} {SOUND}"),
    "P2": ("[cast=dana,leo]", f"{PLACE} A medium two-shot from the waist up: {DANA}, on the left, and {LEO}, on the "
           "right, stand on the sidewalk turned toward each other in three-quarter view, the only two people in the "
           "shot. The camera holds still. Her brows drawn together, Dana says, puzzled, slowing on the word three: "
           "'Three of the streetlights on this block are missing.' Then Leo shrugs and answers, slow and low: "
           f"'Somebody must have taken them in the night.' {LIGHT} {SOUND}"),
    "P4": ("[cast=dana,leo]", f"{PLACE} An over-the-shoulder shot: the back of {LEO}'s head, his grey flat cap and "
           "his navy shoulder fill the lower left foreground, soft and out of focus; beyond him, facing the camera in a "
           f"medium close-up, {DANA}, speaks to him. Leo is silent. The camera holds still. Her brows drawn together, "
           f"her eyes on Leo, Dana {SAYS} {LINE} {LIGHT} {SOUND}"),
    # angle and movement
    "A1": ("[cast=dana]", single(f"A profile shot from the chest up: the camera is at the right side of {ALONE} she "
                                 "faces the left edge of the frame, her face in exact side profile, talking to someone "
                                 "out of frame. The camera holds still.",
                                 cue="Her brows drawn together, her eyes on the person off to the left, she")),
    "M1": ("[cast=dana]", single(f"A walk-and-talk: {ALONE} walks along the sidewalk toward the camera while the "
                                 "camera tracks backward in front of her at the same pace, keeping her in a medium shot "
                                 "from the waist up.", cue="As she walks, her brows drawn together, her eyes on the "
                                 "lens, she")),
    "M2": ("[cast=dana]", single(f"A walk-and-talk from the side: the camera dollies alongside {ALONE} as she walks "
                                 "along the sidewalk from left to right, a medium shot from the waist up, her face in "
                                 "three-quarter view toward the camera, the houses sliding past behind her.",
                                 cue="As she walks, her brows drawn together, her eyes glancing to the lens, she")),
    # the mouth and the timing
    "O1": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera, holding a black "
                                 "handheld microphone close to her mouth, just below her lips, like a television "
                                 "reporter. The camera holds still.", says="says into the microphone, puzzled and "
                                 "precise, slowing on the word three:")),
    "O3": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera. The camera holds "
                                 "still.", cue="She is laughing, delighted and amused, smiling wide, her eyes "
                                 "crinkling, and she", says="says, laughing through the words, bright and giggling:")),
    "T1": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera. The camera holds "
                                 "still. The shot opens on her already speaking, the first word at the very first frame, "
                                 "with no pause before it.", cue="Her brows drawn together, her eyes on the lens, she")),
    "T2": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera. The camera holds "
                                 "still.", cue="She is silent for a long moment, her brows drawn together, then she",
                                 says="says only, quiet and certain:", line="'Three are missing.'",
                                 extra="")),
}
# The [cast] composer draws the first frame at medium scale whatever the line asks (scenes 7-9, 2026-10-03 14:30:
# "full length" and "wide from across the street" came out waist-up). The ladder is redrawn without [cast]: the image
# model composes the shot from the line alone (Dana is fully described in it).
for cid in ("F3", "F4", "F5"):
    CONDITIONS[cid + "n"] = ("", CONDITIONS[cid][1])
    # [layout] (story.sh, 2026-10-03): the composition drawn from the line first, then the cast portrait put into it,
    # so a recurring character can be small in the frame and keep one face
    CONDITIONS[cid + "L"] = ("[cast=dana] [layout]", CONDITIONS[cid][1])

TIER2 = {
    "P3": ("[cast=dana,leo]", f"{PLACE} A medium-wide shot: four neighbours sit on a steep front stoop facing the "
           f"camera: {DANA}, in the middle, {LEO}, beside her, a young man in a red hoodie and an older woman in a green "
           "cardigan, the only four people in the shot. Dana is the only one who speaks; the other three listen with "
           f"their mouths closed, silent. The camera holds still. Her brows drawn together, Dana {SAYS} {LINE} {LIGHT} "
           f"{SOUND}"),
    "M3": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera while the camera "
                                 "slowly circles around her, from her front toward her left side.")),
    "O2": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera, holding a paper "
                                 "coffee cup at her chest. She takes a sip, then lowers the cup to her chest. The camera "
                                 "holds still.")),
    "T3": ("[cast=dana]", single(f"A medium close-up from the chest up on {ALONE} facing the camera. The camera holds "
                                 "still.", says="says quickly, rattling it off without a pause:",
                                 line="'I counted every streetlight on this block twice, from the corner store to the "
                                      "church, and three of them are missing, and nobody on this street even noticed.'")),
    "V1": ("[cast=dana]", single(f"A medium shot from the waist up on {ALONE} standing on the sidewalk facing the "
                                 "camera. The camera holds still.", cue="Her eyes wide, she",
                                 says="shouts across the street, loud and urgent:",
                                 line="'Leo! Three of the streetlights are missing! Come and look at this right now!'")),
    "V2": ("[cast=dana]", single(f"A close-up on the face of {ALONE} facing the camera. The camera holds still.",
                                 cue="Her eyes darting to the side, she", says="whispers, hushed and secretive:")),
    "K1": ("[cast=clown]", f"{PLACE} A medium close-up from the chest up on the clown, a man of about forty, tall and "
           "thin, white face paint, a round red nose, a frizzy bright orange wig, a baggy yellow jumpsuit with big red "
           "polka dots, a white ruffled collar, the only person in the shot, facing the camera. The camera holds still. "
           f"His brows drawn together, his eyes on the lens, he {SAYS} {LINE} Soft blue dusk light, the streetlight's "
           f"warm glow on his face. {SOUND}"),
}
# The hold follow-up (2026-10-04): wide stills come out wide, but the speaker walks to the lens in the video
# (scenes 10-15, 36-41). Five ways to keep a wide speaking shot wide; [hold] needs apply-hold-token.py.
WIDE = ("A wide shot from across the street: " + ALONE + " stands small on the far sidewalk in front of the pastel "
        "houses, about a quarter of the frame's height, facing the camera.")
STAY = ("She stays standing in the same spot on the far sidewalk for the whole shot, her feet planted, and the camera "
        "stays locked off across the street.")
HOLD = {
    "H1": ("", single(f"{WIDE} {STAY}")),
    "H2": ("[hold]", single(f"{WIDE} The camera holds still.")),
    "H3": ("[hold]", single(f"A wide shot from across the street: {ALONE} sits small on a bench on the far sidewalk in "
                            "front of the pastel houses, about a quarter of the frame's height, facing the camera. She stays "
                            "seated. The camera holds still.")),
    "H4": ("[cast=dana] [layout] [hold]", single(f"{WIDE} {STAY}")),
    "H5": ("[hold]", f"{PLACE} A wide shot from across the street: {DANA}, and {LEO}, stand small on the far sidewalk "
           "in front of the pastel houses, about a quarter of the frame's height, turned toward each other, the only two "
           f"people in the shot. {STAY.replace('She stays', 'They stay').replace('her feet', 'their feet')} Her brows "
           "drawn together, Dana says, puzzled, slowing on the word three: 'Three of the streetlights on this block are "
           "missing.' Then Leo shrugs and answers, slow and low: 'Somebody must have taken them in the night.' "
           f"{LIGHT} {SOUND}"),
}

LANDSCAPE = {"L1": CONDITIONS["F1"], "L2": ("", CONDITIONS["F4"][1])}   # the wide one without [cast] (see above)

CAST = ['  "dana|a woman of about forty, short dark curly hair, a mustard-yellow raincoat over a grey sweater, small gold '
        'hoop earrings"',
        '  "leo|a man of about sixty, a short white beard, a navy peacoat, a grey flat cap"']
CLOWN = ('  "clown|a man of about forty, tall and thin, white face paint, a round red nose, a frizzy bright orange wig, a '
         'baggy yellow jumpsuit with big red polka dots, a white ruffled collar, huge red shoes"')
BIBLE = ("Photorealistic live-action, present-day San Francisco, an ordinary 40mm lens, eye-level framing, crisp natural "
         "colour, a clean rectangular full-frame image, real adult actors who resemble no celebrity.")


PORTRAIT_ORDER = ([("C0", s) for s in SEEDS] + [("F1", s) for s in SEEDS] + [("F2", s) for s in SEEDS] +
                  [("F3", s) for s in SEEDS] + [("F4", 4101)] +          # rendered before the 14:30 pause
                  [(c, s) for c in ("F4n", "F5n", "F3n", "P1", "P2", "P4", "A1", "M1", "M2", "O1", "O3", "T1", "T2")
                   for s in SEEDS] +
                  [(c, s) for c in ("F4L", "F5L", "F3L") for s in SEEDS])    # scenes 36-41: needs the [layout] token


def project(name: str, title: str, conds: dict, portrait: int, cast: list[str], order=None) -> str:
    scenes, index = [], []
    order = order or [(cid, sd) for cid in conds for sd in SEEDS]
    for cid, sd in order:
        tok, text = conds[cid]
        if True:
            scenes.append(f'"[noanchor] [still] {tok + " " if tok else ""}[seed={sd}] {text}"')
            index.append(f"#   scene {len(scenes):2}: {cid} seed {sd}")
    return "\n".join([
        f"# {name}: {title}",
        "# Shot lab (docs/data/shot-lab/): one factor at a time, two seeds per condition. No redos:",
        "# the lab measures first takes (SYNC_TRIES=1, SYNC_GATE=report). Scene index:", *index,
        f"NAME={name}; SIZE=720p; SECS=8; SEED=4100; PORTRAIT={portrait}; MODE=\"\"; ANCHOR_STRENGTH=0; ANCHOR_FRAME=16",
        "LAB=1   # a controlled experiment: the dialogue lint's delivery-variety check is off (rig/dialogue.py)",
        "SOUND='a quiet residential street at dusk, distant traffic'",
        "CAST=(", *cast, ")",
        f"BIBLE='{BIBLE}'",
        "SCENES=(", *scenes, ")", ""])


if __name__ == "__main__":
    (HERE / "lab-portrait.txt").write_text(project("lab-shots", "dialogue shot types, portrait 9:16, tier 1",
                                                   CONDITIONS, 1, CAST, PORTRAIT_ORDER))
    (HERE / "lab-landscape.txt").write_text(project("lab-shots-landscape", "dialogue shot types, landscape 16:9",
                                                    LANDSCAPE, 0, CAST))
    (HERE / "lab-portrait-2.txt").write_text(project("lab-shots-2", "dialogue shot types, portrait 9:16, tier 2",
                                                     TIER2, 1, CAST + [CLOWN]))
    (HERE / "lab-hold.txt").write_text(project("lab-shots-hold", "keeping a wide speaking shot wide, portrait 9:16",
                                               HOLD, 1, CAST))
    for f in ("lab-portrait.txt", "lab-landscape.txt", "lab-portrait-2.txt", "lab-hold.txt"):
        t = (HERE / f).read_text(); print(f, t.count('"[noanchor]'), "scenes")
