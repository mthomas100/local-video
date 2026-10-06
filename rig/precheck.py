#!/usr/bin/env python3
"""precheck.py — cheap, model-free checks on rendered scenes (2026-09-23, the local-agent film rig).

    precheck.py <NAME> [scene ...]            # default: every scene-N.mp4 in ~/Videos/vidgen/<NAME>
    precheck.py <NAME> 1 2 3 --json out.json  # also write the full JSON

Why: visual judgment is where a local orchestrator model is weakest, and the defects that cost
renders on 2026-09-23 were coarse: a film-strip border, a rounded or circular mask, a doubled
character, a cartoon cat, a black or frozen clip. Each is measurable from six sampled frames
without a model, so the rig attaches these numbers and a one-line verdict per scene to what the
model sees on a contact sheet. Runs on the CPU (ffmpeg + numpy) plus the same macOS Vision face
call bin/facescore.swift makes; safe beside a render.

Per scene it reports, over 6 frames (every 2.5 s of a 15 s clip):
  border    dark strips along the edges (letterbox, pillarbox, film strip with sprocket holes)
  mask      dark corners with a bright middle: rounded frame or circular/binocular mask
  vignette  1 - outer-ring brightness / centre brightness (soft darkening toward the edges)
  faces     faces per frame (Vision), compared with the people the scene text names
  cartoon   saturation, flat-block fraction, edge density: reported only; measured NOT to separate
            the CGI-cat draft from the photoreal films, so it never flags (see the code comment)
  bright    mean luma per frame; black stretches and a black opening frame
  motion    mean frame-to-frame difference; a frozen clip scores near 0

  bars      (2026-09-24) rows or columns of uniform black running in from an edge, per frame: the
            letterbox LTX-2.5 draws after a cut inside one generation. The strip test above missed
            it in dark scenes (nyc-2000-slavic-neon scene 5, centre luma under 45); uniform-black
            rows do not occur in a real night sky or street (0 rows in every good scene measured)
  transcript (--transcribe) what the audio says, from Parakeet v3 (English and 24 European
            languages) via rig/transcribe.py; only when the GPU is free (the render tools call it
            while the language model is unloaded); cached, so later runs print it without the GPU

Verdict per scene: OK; REDO followed by the hard flags (border, bars, mask, frozen, a black
opening or two black frames: the defect is in the pixels, redo the scene); or LOOK followed by
the soft flags (vignette, faces, a single black-bar frame: look at that row of the sheet). The
REDO class exists because on 2026-09-24 the orchestrator waved off a mask flag as "the look"
and passed a letterboxed scene (the 2026-09-24 run post-mortem).
Results are cached per scene in <film>/.precheck/ keyed by the clip's size and mtime.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:  # /opt/homebrew python has no numpy; the engine's venv does
    venv = Path.home() / "repos/ltx-2-mlx/.venv/bin/python"
    if venv.exists() and os.environ.get("PRECHECK_REEXEC") != "1":
        os.environ["PRECHECK_REEXEC"] = "1"
        os.execv(str(venv), [str(venv), __file__, *sys.argv[1:]])
    raise

HOME = Path.home()
VIDEOS = HOME / "Videos/vidgen"
FACESCORE = HOME / "repos/local-video/bin/facescore.swift"
TRANSCRIBE = HOME / "repos/local-video/rig/transcribe.py"
STT_PYTHON = HOME / "repos/mlx-audio/.venv/bin/python"
FRAMES_PER_SCENE = 6
CACHE_VERSION = "2026-10-03a"   # bump when a check changes, so cached verdicts are recomputed
HARD = ("border", "bars", "mask", "frozen", "black-frames")


def scene_texts(film_dir: Path) -> list[str]:
    """The scene prompts, in order, from the project.txt story.sh copies into the film folder."""
    p = film_dir / "project.txt"
    if not p.exists():
        return []
    txt = p.read_text()
    m = re.search(r"^SCENES=\(\s*\n(.*?)^\)", txt, re.M | re.S)   # CAST=( "..." ) lines are not scenes (2026-09-27)
    return re.findall(r'^"(.*)"$', m.group(1) if m else txt, re.M)


PERSON = re.compile(
    r"\b(?:a|an|the)\s+(?:young\s+|tall\s+|small\s+|heavy\s+|old\s+|elderly\s+)?"
    r"(?:man|woman|mermaid|girl|boy|guy|lady|gentleman|child|teenager|robot|android|humanoid|cyborg)"
    r"\b[^.;]{0,40}?\bof about\b",
    re.I,
)


def expected_faces(text: str) -> int | None:
    """How many people the scene text names (the film skill describes each at first mention as
    'NAME, a man of about N, ...'). 'the only person/man/woman' caps it at 1, 'the two of them are
    the only people' at 2. None when the text names nobody in that form (do not flag)."""
    t = text.lower()
    if re.search(r"\bthe only (person|man|woman|human|one)\b", t):
        return 1
    if re.search(r"\b(two|both) of them are the only\b", t):
        return 2
    n = len(PERSON.findall(t))
    return n or None


def sample_frames(mp4: Path, tmp: Path, n: int = FRAMES_PER_SCENE) -> list[Path]:
    """n frames spread over the clip (2.5 s apart on a 15 s scene), full resolution PNG."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip() or 15)
    step = max(dur / n, 0.5)
    out = tmp / (mp4.stem + "-%02d.png")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp4), "-vf",
                    f"fps=1/{step:.4f}", "-frames:v", str(n), str(out)], check=True)
    return sorted(tmp.glob(mp4.stem + "-*.png"))


def face_counts(paths: list[Path]) -> dict[str, int]:
    """faces per image via bin/facescore.swift (VNDetectFaceCaptureQualityRequest); one swift run."""
    if not paths:
        return {}
    r = subprocess.run(["swift", str(FACESCORE), "1", *map(str, paths)], capture_output=True, text=True)
    counts = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            counts[parts[2]] = int(parts[1])
    return counts


def frame_stats(path: Path) -> dict:
    img = Image.open(path).convert("RGB")
    a = np.asarray(img, dtype=np.float32)
    h, w, _ = a.shape
    luma = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    e = max(int(round(min(h, w) * 0.03)), 2)  # edge strip width
    strips = {"top": luma[:e].mean(), "bottom": luma[-e:].mean(), "left": luma[:, :e].mean(),
              "right": luma[:, -e:].mean()}
    c = max(int(round(min(h, w) * 0.07)), 4)  # corner squares
    cpatch = [luma[:c, :c], luma[:c, -c:], luma[-c:, :c], luma[-c:, -c:]]
    corners = [x.mean() for x in cpatch]
    # a drawn mask or rounded frame is flat black; a night sky or dark wall in a corner has texture (2026-09-27)
    corner_std = float(np.median([x.std() for x in cpatch]))
    mids = [luma[:c, w // 2 - c:w // 2 + c].mean(), luma[-c:, w // 2 - c:w // 2 + c].mean(),
            luma[h // 2 - c:h // 2 + c, :c].mean(), luma[h // 2 - c:h // 2 + c, -c:].mean()]
    ch, cw = int(h * 0.3), int(w * 0.3)
    centre = luma[ch:h - ch, cw:w - cw].mean()
    ring_mask = np.ones_like(luma, dtype=bool)
    rh, rw = int(h * 0.15), int(w * 0.15)
    ring_mask[rh:h - rh, rw:w - rw] = False
    ring = luma[ring_mask].mean()
    vignette = float(max(0.0, 1.0 - ring / centre)) if centre > 1 else 0.0
    # saturation: (max-min)/max per pixel
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0).mean()
    # flat blocks: 8x8 blocks whose luma std is tiny (cartoon fills and black bars have many)
    bh, bw = h // 8 * 8, w // 8 * 8
    blocks = luma[:bh, :bw].reshape(bh // 8, 8, bw // 8, 8).std(axis=(1, 3))
    flat = float((blocks < 2.0).mean())
    # edge density: fraction of pixels with a strong gradient
    gy = np.abs(np.diff(luma, axis=0))[:, :-1]
    gx = np.abs(np.diff(luma, axis=1))[:-1, :]
    edges = float(((gx + gy) > 40).mean())
    # uniform-black bars: rows (top, bottom) or columns (left, right) from the edge whose mean luma
    # is under 12 and whose spread is under 6 (calibrated on nyc-2000-slavic-neon: letterboxed frames
    # 80-200 rows, every good frame 0, dark night frames included)
    rm, rs, cm, cs = luma.mean(axis=1), luma.std(axis=1), luma.mean(axis=0), luma.std(axis=0)

    def run_len(means, stds):
        k = 0
        while k < len(means) // 3 and means[k] < 12 and stds[k] < 6:
            k += 1
        return k
    bars = {"top": run_len(rm, rs), "bottom": run_len(rm[::-1], rs[::-1]),
            "left": run_len(cm, cs), "right": run_len(cm[::-1], cs[::-1])}
    return {"shape": (h, w), "bright": float(luma.mean()), "strips": {k: float(v) for k, v in strips.items()}, "bars": bars,
            "corners": float(np.mean(corners)), "corner_std": corner_std, "edge_mids": float(np.mean(mids)), "centre": float(centre),
            "vignette": vignette, "sat": float(sat), "flat": flat, "edges": edges, "_luma": luma}


def analyse_scene(mp4: Path, text: str, tmp: Path) -> dict:
    frames = sample_frames(mp4, tmp)
    stats = [frame_stats(f) for f in frames]
    n = len(stats)
    flags: list[str] = []
    # border: a strip that is dark in most frames while the middle is not
    dark_sides = []
    # 2026-09-27: a dark edge counts only where the frame also has a uniform-black matte on that side (at least 1% of
    # rows or columns under luma 12 with a spread under 6). A night sky or dark trees at the edge of a portrait frame
    # are dark but not uniform: on 2026-09-26 the old rule flagged 13 of 16 redone takes of halloween-clowns-sf-portrait
    # and drove a 106-minute redo round of strong shots.
    def matte(s, side):
        h, w = s["shape"]
        return s["bars"][side] >= 0.01 * (h if side in ("top", "bottom") else w)
    for side in ("top", "bottom", "left", "right"):
        dark = sum(1 for s in stats if s["strips"][side] < 22 and s["centre"] > 45 and matte(s, side))
        if dark >= max(n - 1, 1):
            dark_sides.append(side)
    if dark_sides:
        kind = "letterbox" if set(dark_sides) <= {"top", "bottom"} else "pillarbox" if set(dark_sides) <= {"left", "right"} else "frame"
        flags.append(f"border:{kind}({','.join(dark_sides)})")
    # bars: a frame is letterboxed when both top and bottom carry uniform-black rows (3% of the height each) of
    # similar height (the shorter at least 0.6 of the longer); pillarboxed likewise on the columns.
    # 2026-10-03 (iteration 7, Thorns and Static): the old "or one side carries 12%" rule sent 8 good takes of a dark
    # portrait film to a redo: a black gown or black sand along the bottom of the frame is uniform black too (bottom
    # runs of 101-335 rows of 1280, luma 0.2-0.3). Every known LTX letterbox had bars on both sides, near-symmetric
    # (nyc-2000-slavic-neon 3 and 5: 96/137, 200/198, 201/197, 172/193, 167/112 rows of 704), while the dark-content
    # runs were one-sided or lopsided (backrooms 33/426, 82/426). A one-sided run is now a soft LOOK ("bars-one-side"),
    # and a frame that is black all over is left to the black-frame check. Evidence:
    # the iteration-7 notes (precheck false positives).
    def boxed(s, h, w):
        if s["bright"] < 12:
            return None
        b = s["bars"]
        def two_sided(x, y, size):
            return x >= 0.03 * size and y >= 0.03 * size and min(x, y) >= 0.6 * max(x, y)
        if two_sided(b["top"], b["bottom"], h):
            return "letterbox"
        if two_sided(b["left"], b["right"], w):
            return "pillarbox"
        if max(b["top"], b["bottom"]) >= 0.12 * h:
            return "one-side:letterbox"
        if max(b["left"], b["right"]) >= 0.12 * w:
            return "one-side:pillarbox"
        return None
    boxes = [boxed(s, *s["shape"]) for s in stats]
    full = [b if b and not b.startswith("one-side") else None for b in boxes]
    nbox = sum(1 for b in full if b)
    nside = sum(1 for b in boxes if b and b.startswith("one-side"))
    if nbox >= 2 and not dark_sides:
        kinds = sorted({b for b in full if b})
        flags.append(f"bars:{'+'.join(kinds)}({nbox}/{n}, from frame {next(i for i, b in enumerate(full) if b) + 1})")
    elif nbox == 1 and not dark_sides:
        flags.append(f"bars-one-frame({full.index(next(b for b in full if b)) + 1}/{n})")
    if nside >= 2 and not dark_sides:
        kinds = sorted({b.split(":")[1] for b in boxes if b and b.startswith("one-side")})
        flags.append(f"bars-one-side:{'+'.join(kinds)}({nside}/{n})")
    # mask: dark corners, bright centre; edge midpoints tell rounded frame from circle
    # frames already counted as black bars are not also a mask (the letterbox darkens the corners too:
    # nyc-2000-slavic-neon scene 3 was reported as mask:partial(4/6) and waved off as "the look")
    # 2026-09-27: and the corners are flat (a drawn mask), not a textured dark picture: with the border rule tightened,
    # dark night close-ups of halloween-clowns-sf-portrait read as mask:rounded-corners/circular (7 of 24 takes).
    corner_dark = sum(1 for s, b in zip(stats, boxes) if not b and s["centre"] > 40 and s["corners"] < 0.3 * s["centre"] and s["corners"] < 40 and s["corner_std"] < 3.0)
    if corner_dark >= max(n - 1, 1) and not dark_sides:
        mids_dark = sum(1 for s in stats if s["edge_mids"] < 0.3 * s["centre"])
        flags.append("mask:circular" if mids_dark >= n - 1 else "mask:rounded-corners")
    elif corner_dark >= 2 and not dark_sides:  # a mask that appears mid-clip (app-developer scene 9, 2026-09-23)
        flags.append(f"mask:partial({corner_dark}/{n})")
    vig = float(np.median([s["vignette"] for s in stats]))
    if vig > 0.6 and not dark_sides and "mask:circular" not in flags:
        flags.append(f"vignette:{vig:.2f}")
    # brightness
    brights = [s["bright"] for s in stats]
    # 2026-10-03: a black frame is black AND flat. Dark-by-design frames are textured: the backrooms of Thorns and
    # Static read luma 7-11 with a spread of 10-31 and were flagged black-frames:3/6 and sent to a redo.
    black = sum(1 for s in stats if s["bright"] < 12 and float(s["_luma"].std()) < 4)
    if black:
        flags.append(f"black-frames:{black}/{n}" + (":opens-black" if brights[0] < 12 and float(stats[0]["_luma"].std()) < 4 else ""))
    # motion: mean abs diff between consecutive sampled frames (downscaled)
    diffs = []
    for a, b in zip(stats, stats[1:]):
        la, lb = a["_luma"], b["_luma"]
        diffs.append(float(np.abs(la[::4, ::4] - lb[::4, ::4]).mean()))
    motion = float(np.median(diffs)) if diffs else 0.0
    if diffs and max(diffs) < 1.5:
        flags.append("frozen")
    # cartoon statistics: reported, NOT flagged. Measured 2026-09-23 on the CGI-cat draft
    # (orange-cat-dreams-toon-draft: sat 0.33-0.44, texture like live action) against the photoreal
    # films (the underwater mermaid scenes score sat 0.85-1.0 and are flat): no cheap pixel statistic
    # separated them, so animation drift is left to the contact sheet.
    sat = float(np.median([s["sat"] for s in stats]))
    flat = float(np.median([s["flat"] for s in stats]))
    edges = float(np.median([s["edges"] for s in stats]))
    # faces
    counts = face_counts(frames)
    faces = [counts.get(str(f), 0) for f in frames]
    expected = expected_faces(text)
    if expected is not None and faces:
        over = sum(1 for c in faces if c > expected)
        if over >= 3:
            flags.append(f"faces>named({max(faces)} vs {expected})")
        if expected >= 1 and max(faces) == 0:
            flags.append("no-face-found")
    for s in stats:
        s.pop("_luma", None)
        s.pop("shape", None)
    return {
        "scene": int(re.search(r"scene-(\d+)", mp4.name).group(1)),
        "file": str(mp4),
        "verdict": verdict(flags),
        "flags": flags,
        "faces": faces,
        "faces_expected": expected,
        "bright": [round(b, 1) for b in brights],
        "motion": round(motion, 2),
        "vignette": round(vig, 2),
        "sat": round(sat, 2), "flat": round(flat, 2), "edges": round(edges, 3),
        "strips": {k: round(float(np.median([s["strips"][k] for s in stats])), 1) for k in ("top", "bottom", "left", "right")},
        "corners": round(float(np.median([s["corners"] for s in stats])), 1),
        "bars": [s["bars"] for s in stats],
    }


def is_hard(flag: str) -> bool:
    if flag.startswith("black-frames"):
        m = re.match(r"black-frames:(\d+)/", flag)
        return ":opens-black" in flag or (m is not None and int(m.group(1)) >= 2)
    # mask:partial is soft (2026-09-26): with letterbox bars caught by their own check, a partial mask is
    # usually a night shot with a bright centre (halloween-clowns-sf shot 12, a yellow raincoat on a dark street,
    # was redone for it); full masks (circular, rounded corners in n-1 frames) stay hard.
    # border is soft too (2026-09-26, film3): "a dark edge strip while the centre is bright" is most portrait night
    # shots (a white tower against black sky and dark trees, a glowing pumpkin on a dark deck): shots 2 and 3 of
    # halloween-clowns-sf-portrait were flagged REDO border:frame / letterbox and redone though strong. A real
    # letterbox or pillarbox is uniform black and stays hard under "bars".
    # mask is soft too (2026-09-27): a drawn circular mask and a night aerial's black sky and water have the same
    # corners (luma about 5, spread under 1.5; orange-cat-app-developer redo-1 scene 9 against
    # halloween-clowns-sf-portrait scene 2), so the pixels cannot tell them apart; the director sees each clip at
    # about 500x290 px a frame since 2026-09-26 and decides. Uniform black bars stay hard.
    return flag.startswith(HARD) and not flag.startswith(("bars-one-frame", "bars-one-side", "mask", "border"))


def verdict(flags: list[str]) -> str:
    """OK, REDO <hard flags> [+ soft], or LOOK <soft flags>."""
    hard = [f for f in flags if is_hard(f)]
    soft = [f for f in flags if not is_hard(f)]
    if hard:
        return "REDO " + " ".join(hard) + (f" (also: {' '.join(soft)})" if soft else "")
    return "LOOK " + " ".join(soft) if soft else "OK"


LIPSYNC = HOME / "repos/local-video/rig/audit/lipsync.py"


def add_lipsync(r: dict, mp4: Path) -> None:
    """Lip sync of a dialogue scene (2026-09-27, rig/audit/lipsync.py: the largest face's mouth opening against the
    speech-band loudness, CPU only). Soft flags: lipsync:off when the mouth does not follow the voice (corr < 0.25 at
    zero lag; in-sync shots of the last three films measured 0.4-0.8), lipsync:face-hidden when the speaker's face is
    visible in under 40% of the frames. The human saw mouths that did not match the words.
    STATUS 2026-09-27 12:40: uncalibrated. It passed shots the human saw out of sync; see `docs/dialogue-sync.md`."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lipsync", LIPSYNC)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        m = mod.measure(mp4)
    except Exception as e:
        r["lipsync"] = {"error": str(e)}
        return
    r["lipsync"] = {k: m.get(k) for k in ("face", "corr0", "best_lag_ms", "best", "talkmove")}
    if (m.get("face") or 0) < 0.4:
        r["flags"].append(f"lipsync:face-hidden({m.get('face')})")
    elif m.get("corr0") is not None and m["corr0"] < 0.25:
        r["flags"].append(f"lipsync:off(corr {m['corr0']}, best {m.get('best')} at {m.get('best_lag_ms')} ms)")
    r["verdict"] = verdict(r["flags"])


GATE = HOME / "repos/local-video/rig/sync/gate.py"


def gate_lines(name: str, scenes: list[int]) -> dict[int, str]:
    """The dialogue-sync gate's verdict line per dialogue scene (rig/sync/gate.py, 2026-09-27; cached per take, so
    this is instant after a render through story.sh, which gates every dialogue clip as it renders)."""
    if not scenes or os.environ.get("SYNC_GATE") == "off":
        return {}
    r = subprocess.run(["python3", str(GATE), name, *map(str, scenes)], capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        m = re.match(r"sync (\d+): ", line)
        if m: out[int(m.group(1))] = line
    return out


def cache_key(mp4: Path, text: str) -> str:
    st = mp4.stat()
    return f"{CACHE_VERSION}:{st.st_size}:{st.st_mtime_ns}:" + hashlib.sha1(text.encode()).hexdigest()[:12]


def transcribe(mp4s: list[Path]) -> dict[str, str]:
    """{path: text} from rig/transcribe.py (Parakeet v3 on mlx-audio's venv; loads the model once)."""
    if not mp4s or not STT_PYTHON.exists():
        return {}
    r = subprocess.run([str(STT_PYTHON), str(TRANSCRIBE), *map(str, mp4s)], capture_output=True, text=True)
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        print(f"precheck: transcription failed: {r.stderr.strip()[-300:]}", file=sys.stderr)
        return {}


def quoted_lines(text: str) -> list[str]:
    """The voiced lines a scene asks for, from rig/dialogue.py (2026-09-27: this pattern allowed only 40 characters of
    voice direction before the quote, so a directed line ("says, low and firm, leaning on the word keep: '...'") was
    not seen as dialogue at all)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import dialogue
    return dialogue.quoted_lines(text)


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    json_out = None
    if "--json" in argv:
        json_out = Path(argv[argv.index("--json") + 1])
        args = [a for a in args if a != str(json_out)]
    if not args:
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    name, scenes = args[0], args[1:]
    film_dir = VIDEOS / name
    if not film_dir.is_dir():
        print(f"precheck: no film folder {film_dir}", file=sys.stderr)
        return 1
    texts = scene_texts(film_dir)
    if not scenes:
        scenes = sorted((int(re.search(r"scene-(\d+)", p.name).group(1)) for p in film_dir.glob("scene-*.mp4")))
    want_transcript = "--transcribe" in argv
    cache_dir = film_dir / ".precheck"
    cache_dir.mkdir(exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for s in scenes:
            i = int(s)
            mp4 = film_dir / f"scene-{i}.mp4"
            if not mp4.exists():
                results.append({"scene": i, "verdict": "MISSING", "flags": ["missing"]})
                continue
            text = texts[i - 1] if i - 1 < len(texts) else ""
            key, cfile = cache_key(mp4, text), cache_dir / f"scene-{i}.json"
            try:
                cached = json.loads(cfile.read_text()) if cfile.exists() else None
            except json.JSONDecodeError:
                cached = None
            if cached and cached.get("key") == key:
                results.append(cached)
                continue
            try:
                r = analyse_scene(mp4, text, tmp)
                r["key"] = key
                r["asked_lines"] = quoted_lines(text)
                # the uncalibrated lipsync proxy (add_lipsync) is retired 2026-09-27: rig/sync/gate.py gives the verdict
                results.append(r)
            except Exception as e:  # one bad scene must not hide the others
                results.append({"scene": i, "verdict": f"ERROR {e}", "flags": ["error"]})
    if want_transcript:
        todo = [Path(r["file"]) for r in results if "file" in r and "transcript" not in r]
        heard = transcribe(todo)
        for r in results:
            if "file" in r and r["file"] in heard:
                r["transcript"] = heard[r["file"]]
    for r in results:
        if "key" in r:
            (cache_dir / f"scene-{r['scene']}.json").write_text(json.dumps(r, indent=1) + "\n")
    sync_lines = gate_lines(name, [r["scene"] for r in results if r.get("asked_lines")])
    for r in results:
        extra = ""
        if "faces" in r:
            exp = r["faces_expected"]
            extra = (f" faces {min(r['faces'])}-{max(r['faces'])}" + (f" (named {exp})" if exp is not None else "")
                     + f", bright {int(np.mean(r['bright']))}, motion {r['motion']}, sat {r['sat']}")
        print(f"scene {r['scene']}: {r['verdict']}{extra}")
        if r.get("asked_lines") or "transcript" in r:
            asked = " / ".join(r.get("asked_lines") or []) or "(no quoted line)"
            print(f"  audio: asked {asked!r}; heard {r['transcript']!r}" if "transcript" in r
                  else f"  audio: asked {asked!r}; not transcribed (the render tools transcribe while the GPU is free)")
        if r.get("scene") in sync_lines:
            print(f"  {sync_lines[r['scene']]}")
    if json_out:
        json_out.write_text(json.dumps(results, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
