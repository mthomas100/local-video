#!/usr/bin/env python3
"""score.py <screenplay.md>... [--bg NAME] [--theme REGEX] — mechanical checks of a film screenplay (2026-10-03 eval).

Brief-neutral by default (2026-10-04): the background-character and theme counts run only when asked for. Before
that, the counts were hardcoded to the clown brief ("clown", Halloween words, San Francisco places), and a model told
to run this checker and "fix what it names" added a silent clown to every shot of a nature-documentary screenplay.

Splits the screenplay into numbered shots and reports what a machine can check; humour and craft are judged
separately (blind). Per screenplay, one JSON line:
  shots, seconds (from [secs]/"N s" in headers, default 8), spoken lines, words per line (and how many sit in the
  measured sync band of 10-18 words for an 8 s shot), speaking shots with more than one quoted speaker cue,
  the rig's dialogue lint (rig/dialogue.py) on each shot, shots that mention the clown, shots with a Halloween
  detail, San Francisco places named, and the share of interview shots whose clown is in the background.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dialogue  # noqa: E402

SHOT = re.compile(r"^\s*(?:#{1,4}\s*)?(?:\*\*)?\s*(?:SHOT|Shot)?\s*(\d{1,2})\s*[.:)\-—]", re.M)
QUOTE = re.compile(r"(?<=[\s:,(])['‘\"“](.{3,300}?)['’\"”](?=[\s.,;:!?)\"]|$)")
HALLOWEEN = re.compile(r"halloween|jack-o|pumpkin|cobweb|skeleton|costume|trick.or.treat|ghost|witch|bat[s ]|candy|"
                       r"day of the dead|marigold|papel picado|spooky|october", re.I)
PLACES = ["golden gate", "transamerica", "bay bridge", "ferry building", "dolores", "mission", "cable car",
          "fisherman", "pier 39", "alcatraz", "coit", "painted ladies", "lombard", "chinatown", "castro",
          "haight", "ocean beach", "crissy", "embarcadero", "union square", "valencia", "noe", "twin peaks",
          "north beach", "presidio", "muni", "bart", "sea lion", "victorian"]
BACKGROUND = re.compile(r"behind|background|far off|across the street|over (?:her|his|their) shoulder|in the distance",
                        re.I)


def shots_of(text):
    marks = [(m.start(), int(m.group(1))) for m in SHOT.finditer(text)]
    # keep a run of increasing shot numbers starting at 1
    seq, want = [], 1
    for pos, n in marks:
        if n == want:
            seq.append(pos); want += 1
    out = []
    for i, pos in enumerate(seq):
        end = seq[i + 1] if i + 1 < len(seq) else len(text)
        out.append(" ".join(text[pos:end].split()))
    return out


def score(path, bg=None, theme=None):
    text = Path(path).read_text(errors="replace")
    shots = shots_of(text)
    secs, lines, multi, clown, hallo, bg_ok, interviews = 0, [], 0, 0, 0, 0, 0
    for s in shots:
        m = re.search(r"(\d{1,2})\s*(?:s\b|sec|seconds)|\[secs=(\d+)\]", s[:200])
        secs += int(m.group(1) or m.group(2)) if m else 8
        q = [x for x in QUOTE.findall(s) if len(x.split()) >= 3]
        lines += q
        if len(set(re.findall(r"\b(says|asks|replies|answers|adds|whispers|shouts)\b", s))) and len(q) > 1:
            multi += 1
        if bg and re.search(bg, s, re.I): clown += 1
        if theme and re.search(theme, s, re.I): hallo += 1
        if bg and q and re.search(bg, s, re.I):
            interviews += 1
            if BACKGROUND.search(s): bg_ok += 1
    wl = [len(x.split()) for x in lines]
    lint = dialogue.lint(["[noanchor] " + s for s in shots]) if shots else []
    low = text.lower()
    out = {"file": str(path), "shots": len(shots), "seconds": secs, "spoken_lines": len(lines),
            "words_per_line_median": sorted(wl)[len(wl) // 2] if wl else 0,
            "lines_in_sync_band_10_18": sum(10 <= w <= 18 for w in wl),
            "shots_multi_quote": multi, "lint_findings": len(lint), "words": len(text.split())}
    if bg: out.update({"shots_with_bg": clown, "speaking_shots_with_bg_behind": f"{bg_ok}/{interviews}"})
    if theme: out["shots_with_theme"] = hallo
    if bg == "clown": out["sf_places"] = sum(p in low for p in PLACES)   # the clown brief's place count, for the bench
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    bg = a[a.index("--bg") + 1] if "--bg" in a else None
    theme = a[a.index("--theme") + 1] if "--theme" in a else None
    files = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--bg", "--theme"))]
    for p in files:
        print(json.dumps(score(p, bg, theme)))
