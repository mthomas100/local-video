#!/usr/bin/env python3
"""review-bench.py — score review designs for the film director against a labelled answer key (2026-09-26).

The director (DeepSeek V4 Flash Vision, `local/vision-q4`) kept both clear misses and every partial shot of the
halloween-clowns-sf film and asked to redo two strong ones.
This bench replays the review step offline, without rendering: the same clips, the lines they were asked to show,
the same model through llama-swap. It scores each review design against the answer key
(rig/bench/review-answer-key-halloween-clowns-sf.json) so the rig adopts the design that sees best.

Designs (the iteration-3 plan (not published)):
  V0  the run's design: contact sheets of up to 6 rows x 4 frames scaled to 1400 px, the asked rows cut at 260
      characters, in the run's three review calls (1-3; 4-16; the redos of 2 and 12).
  V1  bigger frames: one image per clip, a 2x2 grid of its 4 frames, the full asked line.
  V2  blind description first: call 1 shows the V1 images WITHOUT the asked lines and asks for an inventory;
      call 2 (text only, the images replaced by a note, as the rig's context hook does) gives the lines and asks
      for the comparison.
  V3  a checklist: the model first writes yes/no questions per line from the line alone (as it would when
      planning), then answers them on the V1 images.
  V4  an identity board per recurring character: head-and-shoulders crops from every clip it appears in, and
      "which tiles are a different person?" Scored on identity only.
  V5  (optional) any design above on another model: --model qwen27-262k.

ds4 gives every image at most 381 tokens of 42x42 px cells (ds4_image.c, ds4_deepseek4_safe_resize), so a frame's
size inside the image decides what the model can see; the run JSON records the size each image arrives at.

GPU rules: `run` loads the model through llama-swap. Nothing may render meanwhile; it refuses if a render runs, and
`--unload` unloads the model at the end. `prep`, `score` and `selftest` are CPU only.

Usage:
  review-bench.py prep [--designs V0 V1 V4]         # build the images (ffmpeg, PIL, macOS Vision on the CPU)
  review-bench.py run --designs V0 V1 --reps 3 [--model vision-q4-400k] [--stub oracle|keepall] [--unload]
  review-bench.py score [--designs ...] [--tag TAG] # table of scores from rig/bench/results/
  review-bench.py selftest                          # the whole pipeline against stubs, no model
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # /opt/homebrew python has no PIL; the engine's venv does (CPU only here, no MLX import)
    venv = Path.home() / "repos/ltx-2-mlx/.venv/bin/python"
    if venv.exists() and os.environ.get("REVIEW_BENCH_REEXEC") != "1":
        os.environ["REVIEW_BENCH_REEXEC"] = "1"
        os.execv(str(venv), [str(venv), __file__, *sys.argv[1:]])
    raise

HOME = Path.home()
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "rig"))
import review_images as RI  # noqa: E402  the same images review_scenes shows the director
BENCH = REPO / "rig/bench"
RESULTS = BENCH / "results"
DIRECTOR_MD = REPO / "rig/film-director.md"
SWAP = os.environ.get("REVIEW_BENCH_URL", "http://127.0.0.1:8090")

# ---------------------------------------------------------------------------------------------------------------
# Per-key configuration: how the director reviewed in the run, and the identity labels (from the key's cross_shot).
# ---------------------------------------------------------------------------------------------------------------
KEYS = {
    "halloween-clowns-sf": {
        "key": BENCH / "review-answer-key-halloween-clowns-sf.json",
        "first_take_rev": "8735820",   # the project before the redo commit 78cea52 (lines of the first takes)
        "project_path": "stories/projects/17-halloween-clowns-sf.txt",
        # the run's review calls: review_scenes 1 2 3; review_scenes 4..16 (three sheets); review_scenes 2 12
        "groups": [["1", "2t1", "3"], ["4", "5", "6", "7", "8", "9", "10", "11", "12t1", "13", "14", "15", "16"],
                   ["2t2", "12t2"]],
        # identity: tiles per character; pairs listed in "same" are one look, every other pair differs
        "identity": {
            "Marrow": {"tiles": ["5", "6", "10", "13", "15", "16"], "same": [["6", "13"]]},
            "Tatter": {"tiles": ["7", "8"], "same": [["7", "8"]]},
            "Nia": {"tiles": ["9", "11", "12t1"], "same": [["9", "11"]]},
        },
        # which face in a clip with two people is the character: "left" / "right" / "largest" (default)
        "face_pick": {("10", "Marrow"): "left", ("15", "Marrow"): "left", ("12t1", "Nia"): "largest"},
    },
}

CLASSES = ["extra-object", "landmark-lookalike", "city-not-recognisable", "missing", "identity-drift", "blocking"]
KEY_CLASS = {"extra-object": "extra-object", "landmark-lookalike": "landmark-lookalike",
             "landmark-partial": "landmark-lookalike", "city-not-recognisable": "city-not-recognisable",
             "missing": "missing", "weak": "missing", "identity-drift": "identity-drift", "blocking": "blocking"}


def load_key(name: str) -> dict:
    cfg = KEYS[name]
    key = json.loads(cfg["key"].read_text())
    film = Path(os.path.expanduser(key["film_dir"]))
    items = {}
    for it in key["items"]:
        iid = f'{it["shot"]}t{it["take"]}' if "take" in it else str(it["shot"])
        it = dict(it, id=iid, scene=it["shot"])
        cls = set()
        for d in it.get("defects", []):
            c = KEY_CLASS.get(d.split(":", 1)[0].strip())
            if c:
                cls.add(c)
        it["classes"] = sorted(cls)
        items[iid] = it
    final = scene_lines((film / "project.txt").read_text())
    first = scene_lines(subprocess.run(["git", "-C", str(REPO), "show", f'{cfg["first_take_rev"]}:{cfg["project_path"]}'],
                                       capture_output=True, text=True, check=True).stdout)
    for iid, it in items.items():
        lines = first if it.get("take") == 1 else final
        it["line"] = lines[it["scene"] - 1]
        it["path"] = film / it["clip"]
    return {"name": name, "film": film, "items": items, "cfg": cfg}


def scene_lines(txt: str) -> list[str]:
    """The scene texts as the rig shows them (film-rig.ts sceneTexts): quoted lines, leading [tokens] removed."""
    out = []
    for m in re.finditer(r'^"(.*)"$', (re.search(r"^SCENES=\(\s*\n(.*?)^\)", txt, re.M | re.S) or [txt, txt])[1], re.M):
        out.append(re.sub(r"^(\[[^\]]*\] )+", "", m.group(1)))
    return out


# ---------------------------------------------------------------------------------------------------------------
# What ds4 does to an image (a port of ds4_image.c: ds4_deepseek4_grid_tokens / solve_resize / safe_resize)
# ---------------------------------------------------------------------------------------------------------------
def _grid_tokens(h: int, w: int) -> int:
    gh, gw = (h // 14 + 2) // 3, (w // 14 + 2) // 3
    n = gh * (gw + 1) + 2
    if gh & 1:
        n += gw + 1
    if (((gh + 1) // 2) * (gw + 1)) & 1:
        n += 2
    return n


def ds4_resize(width: int, height: int, max_tokens: int = 381) -> tuple[int, int, int]:
    """(width, height, tokens) the DeepSeek V4 vision path resizes an image to."""
    pw, ph = width, height
    if pw > ph * 8:
        pw = ph * 8
    if pw * ph < 147456:
        s = math.sqrt(147456 / (pw * ph))
        pw, ph = max(1, int(pw * s)), max(1, int(ph * s))
    bw, bh = -(-pw // 14) * 14, -(-ph // 14) * 14
    budget = max_tokens
    tokens = _grid_tokens(bh, bw)
    while tokens > max_tokens and budget > 4:
        ratio = ph / pw
        mwf = math.sqrt((budget - 2) / ratio + 0.25) - 0.5
        mhf = mwf * ratio
        if mwf < 1:
            mw, mh = 1, ((budget - 2) // 2) & ~1
            bw, bh = mw * 42, mh * 42
        elif mhf < 2:
            mh = 2
            mw = (budget - 2) // mh - 1
            bw, bh = mw * 42, mh * 42
        else:
            mw, mh = int(mwf), int(mhf) & ~1
            s = min(mw * 42 / pw, mh * 42 / ph)
            bw, bh = int(pw * s / 14) * 14, int(ph * s / 14) * 14
        tokens = _grid_tokens(bh, bw)
        budget -= 1
    return bw, bh, tokens


# ---------------------------------------------------------------------------------------------------------------
# Images (CPU only). Cached in <film>/.review-bench/, next to the film they come from (like .precheck/).
# ---------------------------------------------------------------------------------------------------------------
def duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 8)


def frames(ctx: dict, iid: str, k: int) -> list[Path]:
    """k frames spread over the clip the way sheet.sh takes them (ffmpeg fps=k/duration)."""
    it = ctx["items"][iid]
    d = ctx["film"] / ".review-bench" / "frames" / f"{iid}-k{k}"
    got = sorted(d.glob("f-*.png"))
    if len(got) >= k:
        return got[:k]
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(it["path"]),
                    "-vf", f"fps={k}/{duration(it['path'])}", "-frames:v", str(k), str(d / "f-%02d.png")], check=True)
    return sorted(d.glob("f-*.png"))[:k]


def sheet_v0(ctx: dict, ids: list[str]) -> Path:
    """The rig's sheet: sheet.sh (one row per clip, 4 frames when every clip is <= 10.5 s, else 6; 435 px a frame
    for landscape, 290 for portrait; vstack), then the rig's model copy scaled to 1400 px wide."""
    out = ctx["film"] / ".review-bench" / "V0" / f"sheet-{'-'.join(ids)}-model.png"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    k = 6 if max(duration(ctx["items"][i]["path"]) for i in ids) > 10.5 else 4
    rows = []
    for iid in ids:
        fr = [Image.open(p).convert("RGB") for p in frames(ctx, iid, k)]
        w = 1740 // k if fr[0].width > fr[0].height else 290
        h = round(fr[0].height * w / fr[0].width / 2) * 2
        row = Image.new("RGB", (w * k, h))
        for j, f in enumerate(fr):
            row.paste(f.resize((w, h), Image.BICUBIC), (j * w, 0))
        rows.append(row)
    sheet = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet = sheet.resize((1400, round(sheet.height * 1400 / sheet.width)), Image.BICUBIC)
    sheet.save(out)
    return out


def grid2x2(ctx: dict, iid: str) -> Path:
    """One clip as one image, exactly as review_scenes makes it (rig/review_images.py): its 4 frames in a 2x2 grid at
    half size, with "clip N" drawn in a strip on top (pi delivers a tool result's images apart from its text)."""
    out = ctx["film"] / ".review-bench" / "V1L" / f"clip-{iid}.png"
    if not out.exists():
        RI.grid(ctx["items"][iid]["path"], out, f"clip {ctx['items'][iid]['scene']}")
    return out


def identity_board(ctx: dict, name: str) -> tuple[Path, list[str]]:
    """One character's identity board, as the rig would make it (rig/review_images.py board): a head-and-shoulders
    crop from the best face frame of each clip, labelled, the character's name on top."""
    spec = ctx["cfg"]["identity"][name]
    out = ctx["film"] / ".review-bench" / "V4L" / f"board-{name}.png"
    if not out.exists():
        tiles = [(f"clip {label(t)}", ctx["items"][t]["path"], ctx["cfg"]["face_pick"].get((t, name), "largest"))
                 for t in spec["tiles"]]
        RI.board(out, name, tiles)
    return out, spec["tiles"]


def label(iid: str) -> str:
    """What the model is shown for a clip id: the scene number, plus the take for an old take ("12 take 1")."""
    m = re.fullmatch(r"(\d+)t(\d+)", iid)
    return f"{m.group(1)} take {m.group(2)}" if m else iid


def b64(p: Path) -> dict:
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()}}


def img_meta(p: Path) -> dict:
    with Image.open(p) as im:
        w, h = im.size
    rw, rh, tok = ds4_resize(w, h)
    return {"path": str(p), "size": [w, h], "model_sees": [rw, rh], "tokens": tok}


# ---------------------------------------------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------------------------------------------
def review_section() -> str:
    txt = DIRECTOR_MD.read_text()
    m = re.search(r"^## Reviewing.*?(?=^## )", txt, re.S | re.M)
    return m.group(0).strip() if m else ""


OUTPUT_FORMAT = """Reply format: first your review lines as the rules above say. Then end your reply with one JSON array, one object per clip, like this example (about some other film):
[{"clip": "7", "verdict": "redo", "defects": ["missing: the dog the line asks for is in no frame"], "same_character_as": {"Rosa": ["5"]}}]
"clip" is the clip's number as given to you. "verdict" is "keep" or "redo". "defects" lists what is wrong in the clip, each item starting with one class: extra-object (something in the frame the line did not ask for, such as a vehicle or another person), landmark-lookalike (a named landmark or building drawn as a different or generic one), city-not-recognisable (a named city that reads as a generic one), missing (an asked element absent or wrong: makeup, costume, prop, creature, action), identity-drift (a recurring character who looks like a different person than in another clip you were shown), blocking (people placed or moving other than asked), other. An empty list means nothing is wrong. "same_character_as" maps each named recurring character in the clip to the other clips you were shown where that character has the same face, hair and costume ([] when none match); {} when the clip has no named character."""

STRICT = ("Be strict: the named landmark, place or object must be the one asked for, not a look-alike (a Giza pyramid is "
          "not the Transamerica Pyramid, a clock tower is not Coit Tower, a gondola is not a street cable car), with "
          "nothing extra the words summoned (a van named for scale); the scene opens on its own first sentence (no "
          "prologue, border, mask); photoreal; the named people once each, in the asked makeup and costume; the beat "
          "and the blocking visible.")


SEVERITY = ("Redo only for a miss a viewer would notice at first glance: the named landmark or place is a different or "
            "generic one, a named person lacks the asked face, makeup or costume, the main creature or prop is missing or "
            "the wrong size, an object or person the line did not ask for draws the eye, or the shot is broken (border, "
            "mask, frozen). Keep a clip that shows those things even if small details differ (a few distant cars, extra "
            "signs, a slightly different camera move); write the difference in its line.")


def system_prompt() -> str:
    return ("You are the film director on this Mac. You wrote one line per shot for the LTX-2.5 video model; the "
            "shots are rendered and you now review them to decide which to redo. A redo costs 4 to 25 minutes of "
            "rendering: redo a shot that misses what its line asked for, keep a shot that shows it.\n\n"
            + review_section() + "\n\n" + OUTPUT_FORMAT)


def describe_v0(ctx: dict, ids: list[str], take_of: dict) -> str:
    """film-rig.ts describeSheet, verbatim in shape (the asked text cut at 260 characters, as the run showed it)."""
    rows = []
    for j, iid in enumerate(ids):
        t = ctx["items"][iid]["line"]
        rows.append(f"row {j + 1} = scene {ctx['items'][iid]['scene']} (take {take_of[iid]} of at most 3): "
                    f"{t[:260]}{'...' if len(t) > 260 else ''}")
    n = len(ids)
    return (f"Each contact sheet has one row per scene (scenes {', '.join(str(ctx['items'][i]['scene']) for i in ids)} "
            f"top to bottom, at most {6 if n > 6 else n} rows per image, in order), four to six frames per row spread "
            f"evenly over the clip, left to right.\nWhat each row was asked to show:\n" + "\n".join(rows) + "\n"
            'Write one line per row now, while the sheet is in front of you (it is removed from your context after '
            'this reply): "scene N: asked ... / shows ... / keep or redo". ' + STRICT + " Then compare the rows of "
            "each recurring character: same face, hair and costume, or name the drifting clips. A REDO pre-check "
            "verdict is a redo.")


def take_numbers(ctx: dict, ids: list[str]) -> dict:
    return {iid: ctx["items"][iid].get("take", 1) for iid in ids}


def clip_list(ctx: dict, ids: list[str], take_of: dict, questions: dict | None = None) -> str:
    out = []
    for iid in ids:
        it = ctx["items"][iid]
        out.append(f"clip {it['scene']} (take {take_of[iid]} of at most 3): {it['line']}")
        for q, text in enumerate((questions or {}).get(iid, []), 1):
            out.append(f"  Q{q}. {text}")
    return "\n".join(out)


def images_interleaved(ctx: dict, ids: list[str]) -> tuple[list[dict], list[dict]]:
    """The per-clip images in list order, with no text between them: pi sends a tool result's images together
    after its text, so the only label an image carries is the one drawn on it."""
    parts, meta = [], []
    for iid in ids:
        p = grid2x2(ctx, iid)
        parts.append(b64(p))
        meta.append(img_meta(p))
    return parts, meta


V1_HEAD = ("The images below are one per clip, in the order of the list: each shows four frames spread evenly over "
           "the clip, left to right then top to bottom, with its clip number written at the top.")


def requests_for(design: str, ctx: dict, group: list[str], checklist: dict | None) -> list[dict]:
    """One review = one or two chat requests. Returns [{"messages", "meta", "phase"}]; a phase-2 request's messages
    are completed with the phase-1 reply at run time ("__PREV__")."""
    take_of = take_numbers(ctx, group)
    name = ctx["name"]
    sysm = {"role": "system", "content": system_prompt()}
    scenes = " ".join(str(ctx["items"][i]["scene"]) for i in group)
    if design == "V0":
        per = 6
        chunks = [group[i:i + per] for i in range(0, len(group), per)]
        sheets = [sheet_v0(ctx, c) for c in chunks]
        text = (f"{name}: scenes {scenes}.\n\nContact sheets: " + ", ".join(p.name for p in sheets) + "\n\n"
                + describe_v0(ctx, group, take_of))
        return [{"phase": 1, "messages": [sysm, {"role": "user", "content": [{"type": "text", "text": text}] + [b64(p) for p in sheets]}],
                 "meta": [img_meta(p) for p in sheets]}]
    if design == "V1":
        parts, meta = images_interleaved(ctx, group)
        text = (f"{name}: clips {scenes}. {V1_HEAD}\nWhat each clip was asked to show:\n{clip_list(ctx, group, take_of)}\n"
                'Write one line per clip now, while the images are in front of you: "clip N: asked ... / shows ... / '
                'keep or redo". ' + STRICT + " Then compare the clips of each recurring character: same face, hair and "
                "costume, or name the drifting clips.")
        return [{"phase": 1, "messages": [sysm, {"role": "user", "content": [{"type": "text", "text": text}] + parts}], "meta": meta}]
    if design == "V1c":
        # V1 plus a redo threshold: V1 caught every should-redo clip in rep 1 but redid 3 of 10 strong clips for minor
        # things (distant cars, extra neon, a locked camera). The rule is generic, with nothing from this film.
        parts, meta = images_interleaved(ctx, group)
        text = (f"{name}: clips {scenes}. {V1_HEAD}\nWhat each clip was asked to show:\n{clip_list(ctx, group, take_of)}\n"
                'Write one line per clip now, while the images are in front of you: "clip N: asked ... / shows ... / '
                'keep or redo". ' + STRICT + " " + SEVERITY + " Then compare the clips of each recurring character: same face, "
                "hair and costume, or name the drifting clips.")
        return [{"phase": 1, "messages": [sysm, {"role": "user", "content": [{"type": "text", "text": text}] + parts}], "meta": meta}]
    if design == "V2":
        parts, meta = images_interleaved(ctx, group)
        blind = (f"{name}: clips {scenes}. {V1_HEAD} You get what each clip was asked to show only AFTER this step, so "
                 "describe only what you see.\nFor each clip write an inventory, as specific as the frames allow: every "
                 "person (sex, rough age, face paint or makeup, costume, hair, what they do), every vehicle and every "
                 "other large object, every landmark, building or bridge (its shape and material), the place and the "
                 "time of day, the shot size and the camera move. Write \"none\" for a category that is absent. Do not "
                 "guess what was intended and do not judge yet: no verdicts and no JSON in this reply.")
        u1 = {"role": "user", "content": [{"type": "text", "text": blind}] + parts}
        u1_after = {"role": "user", "content": [{"type": "text", "text": blind}] + [
            {"type": "text", "text": f"clip {ctx['items'][i]['scene']}: [image: shown to you once, then removed]"} for i in group]}
        compare = ("Now, what each clip was asked to show:\n" + clip_list(ctx, group, take_of) + "\n"
                   "Compare each line with YOUR inventory above, not with what the line leads you to expect. "
                   'Write one line per clip: "clip N: asked ... / shows ... / keep or redo". ' + STRICT + " Then compare "
                   "the clips of each recurring character: same face, hair and costume, or name the drifting clips.")
        return [{"phase": 1, "messages": [sysm, u1], "meta": meta, "no_json": True},
                {"phase": 2, "messages": [sysm, u1_after, "__PREV__", {"role": "user", "content": compare}], "meta": []}]
    if design == "V3":
        parts, meta = images_interleaved(ctx, group)
        text = (f"{name}: clips {scenes}. {V1_HEAD}\nWhat each clip was asked to show, with the yes/no questions you "
                f"wrote for it when you planned the shots:\n{clip_list(ctx, group, take_of, checklist)}\n"
                "For each clip, answer every question yes or no from the frames (\"clip N: Q1 yes, Q2 no, ...\"), then "
                "write keep or redo: a \"no\" on the landmark, a named person, a creature or prop, or an extra object is "
                "a redo. Then compare the clips of each recurring character: same face, hair and costume, or name the "
                "drifting clips.")
        return [{"phase": 1, "messages": [sysm, {"role": "user", "content": [{"type": "text", "text": text}] + parts}], "meta": meta}]
    raise ValueError(design)


def checklist_request(ctx: dict) -> dict:
    lines = "\n".join(f"line {iid}: {it['line']}" for iid, it in ctx["items"].items())
    ask = ("For each shot line below, write 3 to 6 yes/no questions that a strict reviewer can answer from four frames "
           "of the rendered clip, to check that the clip shows what the line asks and nothing it should not. Cover: "
           "the named landmark or place (its physical features, from the line); each named person (makeup, costume, "
           "hair, age); how many people; the size of creatures and props against the people; anything the wording "
           "might make the video model draw that should not be there (an object named only for comparison or scale); "
           "the shot size and camera move. Phrase every question so that \"yes\" means the clip is right.\n\n"
           f"{lines}\n\nReply with one JSON object only, keyed by the line id: "
           '{"1": ["Is ...?", "..."], "2t1": ["..."]}')
    return {"messages": [{"role": "system", "content": "You are the film director on this Mac, planning how you will check each shot once it is rendered."},
                         {"role": "user", "content": ask}]}


def identity_request(ctx: dict) -> dict:
    sysm = {"role": "system", "content": "You are the film director on this Mac, checking that each recurring character stays the same person from shot to shot."}
    parts, meta, boards, listing = [], [], {}, []
    for j, name in enumerate(ctx["cfg"]["identity"], 1):
        p, tiles = identity_board(ctx, name)
        boards[name] = tiles
        listing.append(f"image {j}: {name} ({character_description(ctx, name)}); tiles " + ", ".join(f"clip {label(t)}" for t in tiles))
        parts.append(b64(p))
        meta.append(img_meta(p))
    text = ("Identity check for the film " + ctx["name"] + ". Each image below is a board for one recurring character: "
            "head-and-shoulders crops of that character from different clips, each tile labelled with its clip. For "
            "each board, group the tiles by person: tiles that show the same person (same face, same makeup, same hair, "
            "same costume) go in one group; a tile that shows a different-looking person goes in its own group. Then "
            "name the tiles that differ from the character's majority look.\nEnd your reply with one JSON array: "
            '[{"character": "Rosa", "groups": [["3", "5"], ["8"]], "differ": ["8"]}] using the clip labels as written '
            "on the tiles.\nThe boards, in order (each has the character's name on top):\n" + "\n".join(listing))
    return {"messages": [sysm, {"role": "user", "content": [{"type": "text", "text": text}] + parts}], "meta": meta, "boards": boards}


def identity_request_blind(ctx: dict) -> dict:
    """V4b: the V4 boards with no name and no description on them or in the text, to test whether naming the character
    ("a board for Marrow, a man of about forty ...") primes the model to see one person everywhere."""
    sysm = {"role": "system", "content": "You compare faces in film frames."}
    parts, meta, listing = [], [], []
    for j, name in enumerate(ctx["cfg"]["identity"], 1):
        spec = ctx["cfg"]["identity"][name]
        out = ctx["film"] / ".review-bench" / "V4b" / f"board-{j}.png"
        if not out.exists():
            RI.board(out, f"board {j}", [(f"clip {label(t)}", ctx["items"][t]["path"],
                                          ctx["cfg"]["face_pick"].get((t, name), "largest")) for t in spec["tiles"]])
        listing.append(f"image {j}: board {j}; tiles " + ", ".join(f"clip {label(t)}" for t in spec["tiles"]))
        parts.append(b64(out))
        meta.append(img_meta(out))
    text = ("Each image below is a board of head-and-shoulders crops from different clips, each tile labelled with its clip. "
            "For each board, group the tiles by person: tiles that show the same person (same face, same makeup, same hair, "
            "same costume) go in one group; a tile that shows a different-looking person goes in its own group. Judge only "
            "what you see.\nEnd your reply with one JSON array: "
            '[{"board": 1, "groups": [["3", "5"], ["8"]]}] using the clip labels as written on the tiles.\n' + "\n".join(listing))
    return {"messages": [sysm, {"role": "user", "content": [{"type": "text", "text": text}] + parts}], "meta": meta}


def parse_identity_blind(text: str, ctx: dict) -> dict:
    names = list(ctx["cfg"]["identity"])
    arr = last_json(text, list, lambda v: all(isinstance(x, dict) for x in v)) or []
    out = {}
    for o in arr:
        try:
            name = names[int(str(o.get("board")).strip()) - 1]
        except (ValueError, IndexError):
            continue
        out[name] = {"groups": [[norm_tile(t) for t in g] for g in o.get("groups") or [] if isinstance(g, list)], "differ": []}
    return out


def character_description(ctx: dict, name: str) -> str:
    for it in ctx["items"].values():
        m = re.search(re.escape(name) + r"(?:'s face alone)?, (an? (?:man|woman)[^,]*,[^,]*,[^,]*,[^,.]*)", it["line"])
        if m:
            return m.group(1).strip()
    return name


# ---------------------------------------------------------------------------------------------------------------
# The model call and the stubs
# ---------------------------------------------------------------------------------------------------------------
def gpu_state(samples: int = 3) -> tuple[float, float]:
    """(mean GPU Device Utilization %, GB of system memory the GPU has in use), from ioreg (no sudo). Catches GPU
    jobs this script does not know by name: on 2026-09-26 a ComfyUI Trellis2 job held the GPU and a bench request
    waited 12 minutes inside ds4's vision encoder."""
    import re as _re, time as _time
    util, mem = [], 0.0
    for i in range(samples):
        out = subprocess.run(["ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"], capture_output=True, text=True).stdout
        m = _re.search(r'"Device Utilization %"=(\d+)', out)
        util.append(float(m.group(1)) if m else 0.0)
        m = _re.search(r'"In use system memory"=(\d+)', out)
        mem = max(mem, int(m.group(1)) / 1e9 if m else 0.0)
        if i + 1 < samples:
            _time.sleep(1)
    return sum(util) / len(util), mem


def other_gpu_jobs() -> str:
    """Known GPU users that are not ours (ComfyUI and 3D/image jobs of other sessions), by port and name."""
    if subprocess.run(["lsof", "-nP", "-iTCP:8189", "-sTCP:LISTEN"], capture_output=True).returncode == 0:
        return "a ComfyUI server listens on :8189"
    r = subprocess.run(["pgrep", "-fl", "ComfyUI|main[.]py --port|[t]rellis|[h]unyuan3d|[P]ixal3D|mflux-generat[e]"], capture_output=True, text=True)
    return f"other GPU processes: {r.stdout.strip()[:200]}" if r.returncode == 0 else ""


def render_running() -> bool:
    return subprocess.run(["pgrep", "-f", "ltx-2-mlx generat[e]"], capture_output=True).returncode == 0


def call_model(model: str, messages: list, max_tokens: int, effort: str) -> dict:
    # By name and port only: once the model is loaded, ioreg's utilization includes the model server's own work.
    other = other_gpu_jobs()
    if other or render_running():
        sys.exit(f"review-bench: {other or 'a render is running'}; pausing rather than competing with it")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "reasoning_effort": effort, "stream": False}
    req = urllib.request.Request(f"{SWAP}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        j = json.loads(r.read())
    msg = j["choices"][0]["message"]
    return {"content": msg.get("content") or "", "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
            "finish": j["choices"][0].get("finish_reason"), "usage": j.get("usage", {}), "seconds": round(time.time() - t0, 1)}


def stub_reply(kind: str, ctx: dict, group: list[str], phase_no_json: bool) -> dict:
    if phase_no_json:
        return {"content": "clip inventory (stub)", "reasoning": "", "finish": "stop", "usage": {}, "seconds": 0}
    arr = []
    for iid in group:
        it = ctx["items"][iid]
        if kind == "oracle":
            same = {}
            if it.get("character"):
                for name in re.findall(r"[A-Z][a-z]+", it["character"]):
                    same[name] = []
            arr.append({"clip": str(it["scene"]), "verdict": "redo" if it["should_redo"] else "keep",
                        "defects": [f"{c}: stub" for c in it["classes"]], "same_character_as": same})
        else:
            arr.append({"clip": str(it["scene"]), "verdict": "keep", "defects": [], "same_character_as": {}})
    return {"content": "stub review lines\n```json\n" + json.dumps(arr) + "\n```", "reasoning": "", "finish": "stop",
            "usage": {}, "seconds": 0}


def stub_checklist(ctx: dict) -> dict:
    return {"content": json.dumps({iid: ["Is the landmark right?", "Is there any vehicle? (no = right)"] for iid in ctx["items"]}),
            "reasoning": "", "finish": "stop", "usage": {}, "seconds": 0}


def stub_identity(kind: str, ctx: dict) -> dict:
    arr = []
    for name, spec in ctx["cfg"]["identity"].items():
        if kind == "oracle":
            groups, seen = [], set()
            for a, b in spec["same"]:
                groups.append([label(a), label(b)])
                seen |= {a, b}
            groups += [[label(t)] for t in spec["tiles"] if t not in seen]
        else:
            groups = [[label(t) for t in spec["tiles"]]]
        arr.append({"character": name, "groups": groups, "differ": []})
    return {"content": json.dumps(arr), "reasoning": "", "finish": "stop", "usage": {}, "seconds": 0}


# ---------------------------------------------------------------------------------------------------------------
# Parsing (tolerant) and scoring
# ---------------------------------------------------------------------------------------------------------------
def last_json(text: str, want: type, ok=lambda v: True):
    """The last top-level JSON value of type `want` (for which ok(value) holds) in the text, fenced or bare, or None.
    A value that parses is skipped whole, so the lists inside an array (its "defects") never count as the answer."""
    dec = json.JSONDecoder()
    opener = "[" if want is list else "{"
    best = None
    pos = 0
    while True:
        i = text.find(opener, pos)
        if i < 0:
            break
        try:
            v, end = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            pos = i + 1
            continue
        if isinstance(v, want) and v and ok(v):
            best = v
        pos = end
    if best is None:  # trailing commas, the commonest slip
        cleaned = re.sub(r",\s*([\]}])", r"\1", text)
        if cleaned != text:
            return last_json(cleaned, want, ok)
    return best


def parse_review(text: str, ctx: dict, group: list[str]) -> dict:
    """{item id: {"verdict", "classes", "defects", "same"}} for the clips of one review call."""
    by_scene = {str(ctx["items"][i]["scene"]): i for i in group}
    out = {}
    arr = last_json(text, list, lambda v: all(isinstance(x, dict) for x in v)) or []
    for o in arr:
        c = re.sub(r"[^0-9]", "", str(o.get("clip", "")).split("take")[0])
        iid = by_scene.get(c)
        if not iid:
            continue
        defects = [str(d) for d in o.get("defects") or []]
        cls = sorted({d.split(":", 1)[0].strip().lower() for d in defects if ":" in d} & set(CLASSES))
        out[iid] = {"verdict": "redo" if str(o.get("verdict", "")).lower().startswith("redo") else "keep",
                    "classes": cls, "defects": defects, "same": o.get("same_character_as") or {}}
    for iid in group:  # fallback: the review line "clip/scene N: ... keep|redo"
        if iid in out:
            continue
        sc = str(ctx["items"][iid]["scene"])
        m = None
        for m in re.finditer(rf"(?:clip|scene)\s*{sc}\b[^\n]*?\b(keep|redo)\b", text, re.I):
            pass
        if m:
            out[iid] = {"verdict": m.group(1).lower(), "classes": [], "defects": [], "same": {}, "from": "line"}
    return out


def parse_identity(text: str) -> dict:
    arr = last_json(text, list, lambda v: all(isinstance(x, dict) for x in v)) or []
    out = {}
    for o in arr:
        if isinstance(o, dict) and o.get("character"):
            groups = [[norm_tile(t) for t in g] for g in o.get("groups") or [] if isinstance(g, list)]
            out[str(o["character"])] = {"groups": groups, "differ": [norm_tile(t) for t in o.get("differ") or []]}
    return out


def norm_tile(t) -> str:
    s = str(t).lower().replace("clip", "").strip()
    m = re.fullmatch(r"(\d+)\s*(?:take\s*(\d+))?", s)
    if not m:
        return s
    return f"{m.group(1)}t{m.group(2)}" if m.group(2) else m.group(1)


def score_review(ctx: dict, verdicts: dict) -> dict:
    items = ctx["items"]
    should = [i for i, it in items.items() if it["should_redo"]]
    strong = [i for i, it in items.items() if it["verdict"] == "strong"]
    got = lambda i: verdicts.get(i, {}).get("verdict")
    said = {i: ("redo" if it.get("director_said", "").lower().startswith("redo") else "keep") for i, it in items.items()}
    s = {"redo_recall": sum(got(i) == "redo" for i in should) / len(should),
         "agree_with_run": sum(got(i) == said[i] for i in items) / len(items),
         "false_redo": sum(got(i) == "redo" for i in strong) / len(strong),
         "redos": sorted((i for i in items if got(i) == "redo"), key=sort_key),
         "unparsed": sorted((i for i in items if i not in verdicts), key=sort_key)}
    for c in CLASSES:
        pos = [i for i, it in items.items() if c in it["classes"]]
        hit = sum(c in verdicts.get(i, {}).get("classes", []) for i in pos)
        fp = sum(c in verdicts.get(i, {}).get("classes", []) for i in items if i not in pos)
        s[f"{c}_recall"] = hit / len(pos) if pos else None
        s[f"{c}_fp"] = fp
    return s


def score_identity(ctx: dict, parsed: dict) -> dict:
    same_hit = same_n = diff_hit = diff_n = 0
    looks = {}
    for name, spec in ctx["cfg"]["identity"].items():
        groups = parsed.get(name, {}).get("groups") or []
        where = {t: gi for gi, g in enumerate(groups) for t in g}
        looks[name] = len(groups)
        same = {frozenset(p) for p in spec["same"]}
        tiles = spec["tiles"]
        for x in range(len(tiles)):
            for y in range(x + 1, len(tiles)):
                a, b = tiles[x], tiles[y]
                model_same = a in where and b in where and where[a] == where[b]
                if frozenset((a, b)) in same:
                    same_n += 1
                    same_hit += model_same
                else:
                    diff_n += 1
                    diff_hit += not model_same
    return {"drift_recall": diff_hit / diff_n if diff_n else None, "same_kept": same_hit / same_n if same_n else None,
            "looks": looks, "looks_key": {n: len(s["tiles"]) - len(s["same"]) for n, s in ctx["cfg"]["identity"].items()}}


def sort_key(iid: str):
    m = re.fullmatch(r"(\d+)(?:t(\d+))?", iid)
    return (int(m.group(1)), int(m.group(2) or 9)) if m else (999, 0)


# ---------------------------------------------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------------------------------------------
def cmd_prep(ctx: dict, designs: list[str]) -> None:
    for d in designs:
        if d in ("V0",):
            for g in ctx["cfg"]["groups"]:
                for c in [g[i:i + 6] for i in range(0, len(g), 6)]:
                    print(json.dumps(img_meta(sheet_v0(ctx, c))))
        if d in ("V1", "V2", "V3"):
            for iid in ctx["items"]:
                print(json.dumps(img_meta(grid2x2(ctx, iid))))
        if d == "V4":
            for name in ctx["cfg"]["identity"]:
                p, _ = identity_board(ctx, name)
                print(json.dumps(img_meta(p)))


def cmd_run(ctx: dict, designs: list[str], reps: int, model: str, stub: str | None, tag: str,
            max_tokens: int, effort: str) -> list[Path]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    written = []
    if not stub:
        util, mem = gpu_state()
        try:
            loaded = json.load(urllib.request.urlopen(f"{SWAP}/running", timeout=5)).get("running", [])
        except Exception:
            loaded = []
        if other_gpu_jobs():
            sys.exit(f"review-bench: {other_gpu_jobs()}; not starting")
        if not loaded and (util > 15 or mem > 10):
            sys.exit(f"review-bench: another job holds the GPU ({util:.0f}% busy, {mem:.1f} GB in use) with nothing loaded here")
    for rep in range(1, reps + 1):
        for d in designs:
            if not stub and render_running():
                sys.exit("review-bench: a render is running; the GPU rules forbid a model call now")
            out = RESULTS / f"{ctx['name']}-{d}-{tag}-r{rep}.json"
            if out.exists():
                print(f"skip {out.name} (exists)")
                written.append(out)
                continue
            rec = {"design": d, "rep": rep, "model": model if not stub else f"stub:{stub}", "effort": effort,
                   "max_tokens": max_tokens, "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "calls": []}
            ask = (lambda m: stub_reply(stub, ctx, [], False)) if stub else None
            if d in ("V4", "V4b"):
                r = identity_request(ctx) if d == "V4" else identity_request_blind(ctx)
                rep_ = stub_identity(stub, ctx) if stub else call_model(model, r["messages"], max_tokens, effort)
                if stub and d == "V4b":  # the stub answers in the named form; map it to boards
                    rep_ = dict(rep_, content=json.dumps([{"board": i + 1, "groups": o["groups"]} for i, o in enumerate(json.loads(rep_["content"]))]))
                parsed = parse_identity(rep_["content"]) if d == "V4" else parse_identity_blind(rep_["content"], ctx)
                rec["calls"].append({"phase": 1, "meta": r["meta"], "reply": rep_, "parsed": parsed})
                rec["identity"] = score_identity(ctx, parsed)
            else:
                checklist = None
                if d == "V3":
                    cr = checklist_request(ctx)
                    # 18 lines x 3-6 questions plus reasoning overflowed 6000 tokens (2026-09-26, rep 1): give it room
                    rep_ = stub_checklist(ctx) if stub else call_model(model, cr["messages"], max(max_tokens, 16000), effort)
                    checklist = last_json(rep_["content"], dict) or {}
                    rec["calls"].append({"phase": 0, "reply": rep_, "checklist": checklist})
                verdicts = {}
                for g in ctx["cfg"]["groups"]:
                    prev = None
                    for r in requests_for(d, ctx, g, checklist):
                        msgs = [({"role": "assistant", "content": prev["content"]} if m == "__PREV__" else m) for m in r["messages"]]
                        rep_ = stub_reply(stub, ctx, g, r.get("no_json", False)) if stub else call_model(model, msgs, max_tokens, effort)
                        call = {"phase": r["phase"], "group": g, "meta": r["meta"], "reply": rep_}
                        if not r.get("no_json"):
                            call["parsed"] = parse_review(rep_["content"], ctx, g)
                            verdicts.update(call["parsed"])
                        rec["calls"].append(call)
                        prev = rep_
                        print(f"{d} r{rep} group {g[0]}..{g[-1]} phase {r['phase']}: {rep_['seconds']} s, "
                              f"finish={rep_['finish']}, {len(rep_['content'])} chars", flush=True)
                rec["verdicts"] = verdicts
                rec["score"] = score_review(ctx, verdicts)
            rec["seconds"] = round(sum(c["reply"]["seconds"] for c in rec["calls"]), 1)
            out.write_text(json.dumps(rec, indent=1))
            written.append(out)
            print(f"wrote {out.name}: {json.dumps(rec.get('score') or rec.get('identity'))}", flush=True)
    return written


def cmd_score(ctx: dict, designs: list[str] | None, tag: str | None) -> str:
    rows = {}
    for p in sorted(RESULTS.glob(f"{ctx['name']}-*.json")):
        rec = json.loads(p.read_text())
        t = p.stem.split("-")[-2]
        if (designs and rec["design"] not in designs) or (tag and t != tag) or rec["model"].startswith("stub"):
            continue
        rows.setdefault((rec["design"], rec["model"], t), []).append(rec)
    lines = ["| design | model | reps | redo recall | false redo | agrees with the run's director | " + " | ".join(CLASSES) + " | identity drift recall / same kept | s per rep |",
             "|---|---|---|---|---|---|" + "---|" * len(CLASSES) + "---|---|"]
    fmt = lambda xs: "-" if not xs else (f"{statistics.mean(xs):.2f}" + (f" ±{statistics.stdev(xs):.2f}" if len(xs) > 1 else ""))
    for (d, m, t), recs in sorted(rows.items()):
        if d in ("V4", "V4b"):
            ids = [r["identity"] for r in recs]
            cells = ["-", "-", "-"] + ["-"] * len(CLASSES) + [f"{fmt([i['drift_recall'] for i in ids])} / {fmt([i['same_kept'] for i in ids])}"]
        else:
            sc = [r["score"] for r in recs]
            cells = [fmt([s["redo_recall"] for s in sc]), fmt([s["false_redo"] for s in sc]), fmt([s["agree_with_run"] for s in sc])]
            for c in CLASSES:
                vals = [s[f"{c}_recall"] for s in sc if s[f"{c}_recall"] is not None]
                fps = [s[f"{c}_fp"] for s in sc]
                cells.append(f"{fmt(vals)} (fp {statistics.mean(fps):.1f})")
            cells.append("-")
        lines.append(f"| {d} | {m} | {len(recs)} | " + " | ".join(cells) + f" | {statistics.mean(r['seconds'] for r in recs):.0f} |")
    return "\n".join(lines)


def cmd_matrix(ctx: dict, tag: str | None) -> str:
    """Per clip: the key's verdict and should_redo, then each design's redo count over its reps."""
    by = {}
    for p in sorted(RESULTS.glob(f"{ctx['name']}-*.json")):
        rec = json.loads(p.read_text())
        t = p.stem.split("-")[-2]
        if rec["model"].startswith("stub") or (tag and t != tag) or "verdicts" not in rec:
            continue
        by.setdefault(rec["design"], []).append(rec["verdicts"])
    designs = sorted(by)
    lines = ["| clip | key | should redo | " + " | ".join(f"{d} ({len(by[d])} reps)" for d in designs) + " |",
             "|---|---|---|" + "---|" * len(designs)]
    for iid in sorted(ctx["items"], key=sort_key):
        it = ctx["items"][iid]
        cells = [f"{sum(v.get(iid, {}).get('verdict') == 'redo' for v in by[d])}/{len(by[d])}" for d in designs]
        lines.append(f"| {label(iid)} | {it['verdict']} | {'yes' if it['should_redo'] else ''} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def cmd_selftest(ctx: dict) -> None:
    import tempfile
    global RESULTS
    real = RESULTS
    with tempfile.TemporaryDirectory() as tmp:
        RESULTS = Path(tmp)
        for kind in ("oracle", "keepall"):
            outs = cmd_run(ctx, ["V0", "V1", "V1c", "V2", "V3", "V4", "V4b"], 1, "stub", kind, f"self{kind}", 4000, "medium")
            for o in outs:
                rec = json.loads(o.read_text())
                if rec["design"] in ("V4", "V4b"):
                    i = rec["identity"]
                    ok = (i["drift_recall"] == 1 and i["same_kept"] == 1) if kind == "oracle" else (i["drift_recall"] == 0)
                else:
                    s = rec["score"]
                    ok = (s["redo_recall"] == 1 and s["false_redo"] == 0 and not s["unparsed"]
                          and all(s[f"{c}_recall"] in (1, None) for c in CLASSES)) if kind == "oracle" else (s["redo_recall"] == 0)
                print(f"selftest {kind} {rec['design']}: {'ok' if ok else 'FAIL'}")
                if not ok:
                    print(json.dumps(rec.get("score") or rec.get("identity")))
                    sys.exit(1)
    RESULTS = real
    # the parser on replies the model is likely to write
    g = ctx["cfg"]["groups"][2]
    txt = 'scene 2: asked ... / shows ... / keep\n```json\n[{"clip": "2", "verdict": "keep", "defects": [],},\n{"clip": "12 take 2", "verdict": "Redo", "defects": ["blocking: x"]}]\n```'
    p = parse_review(txt, ctx, g)
    assert p["2t2"]["verdict"] == "keep" and p["12t2"]["verdict"] == "redo" and p["12t2"]["classes"] == ["blocking"], p
    p = parse_review("clip 2: asked a bridge / shows it / keep\nclip 12: asked / shows / REDO", ctx, g)
    assert p["2t2"]["verdict"] == "keep" and p["12t2"]["verdict"] == "redo", p
    assert ds4_resize(1400, 1158)[:2] == (812, 672) and ds4_resize(1286, 710)[2] <= 381
    print("selftest parser and resize: ok")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n", 1)[1])
    ap.add_argument("cmd", choices=["prep", "run", "score", "matrix", "selftest"])
    ap.add_argument("--key", default="halloween-clowns-sf", choices=sorted(KEYS))
    ap.add_argument("--designs", nargs="*", default=None)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--model", default="vision-q4-400k")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--max-tokens", type=int, default=16384, help="per reply; pi gives local/vision-q4-400k 16384 (~/.pi/agent/models.json)")
    ap.add_argument("--stub", choices=["oracle", "keepall"])
    ap.add_argument("--tag", default=None, help="a label for this run's result files (default: the model name)")
    ap.add_argument("--unload", action="store_true", help="GET /unload on llama-swap when done")
    a = ap.parse_args()
    ctx = load_key(a.key)
    designs = a.designs or ["V0", "V1", "V2", "V3", "V4"]
    if a.cmd == "prep":
        cmd_prep(ctx, designs)
    elif a.cmd == "run":
        try:
            cmd_run(ctx, designs, a.reps, a.model, a.stub, a.tag or a.model, a.max_tokens, a.effort)
        finally:
            if a.unload and not a.stub:
                urllib.request.urlopen(f"{SWAP}/unload", timeout=300).read()
                print("unloaded")
        print(cmd_score(ctx, designs, a.tag or a.model))
    elif a.cmd == "score":
        print(cmd_score(ctx, a.designs, a.tag))
    elif a.cmd == "matrix":
        print(cmd_matrix(ctx, a.tag))
    else:
        cmd_selftest(ctx)


if __name__ == "__main__":
    main()
