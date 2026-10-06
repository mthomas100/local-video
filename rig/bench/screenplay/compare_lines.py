#!/usr/bin/env python3
"""compare_lines.py <screenplay.md> <project.txt> — did the director copy every shot and spoken line word for word?

Splits the screenplay into numbered shots (score.py's parser) and the project into SCENES lines, then compares, shot
by shot, the single-quoted spoken spans (three words or more). It also runs the rig's dialogue lint on the project
lines. Exit 0 when the shot counts match, every line matches and the lint is clean. Used in iteration 6 to check that
pi copied all 22 shots and 19 lines of Clown Sighting.
"""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rig"))
import score  # noqa: E402
import dialogue  # noqa: E402

Q = re.compile(r"(?<=[\s:,])'(.{2,300}?)'(?=[\s.,;:!?)\"]|$)")


def spoken(text):
    return [x for x in Q.findall(text) if len(x.split()) >= 3]


def main(sp, pj):
    want = score.shots_of(Path(sp).read_text())
    got = re.findall(r'^"(.*)"\s*$', Path(pj).read_text(), re.M)
    ok = len(want) == len(got)
    print(f"shots: screenplay {len(want)}, project {len(got)}" + ("" if ok else "  <-- MISMATCH"))
    for i, (w, g) in enumerate(zip(want, got), 1):
        if spoken(w) != spoken(g):
            ok = False
            print(f"shot {i}: lines differ\n  screenplay: {spoken(w)}\n  project:    {spoken(g)}")
    lint = dialogue.lint(got)
    for m in lint:
        print("lint:", m)
    print("ALL LINES WORD FOR WORD, LINT CLEAN" if ok and not lint else "CHECK THE LINES ABOVE")
    sys.exit(0 if ok and not lint else 1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
