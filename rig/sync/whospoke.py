#!/usr/bin/env python3
"""whospoke.py — who spoke the line, as one picture for the director's review (2026-10-04).

Why: the sync gate checks that ONE face moves in time with the voice; it cannot tell whose face that is. In
the iteration-9 film, shot 3, the minister spoke the king's line: the gate passed it (one mouth in sync, no second mouth),
and the director kept it, because on its review sheet the faces were small and the four frames were spread over the
whole clip. This draws, for a speaking shot with two or more faces, the named speaker's [cast] portrait (its face)
beside one row per face on screen, the same moments of the spoken line in every row, and frames in green the face
the gate's own measure picks as the one moving with the voice (SyncNet, as syncmeter.measure does). The director's
question becomes "is the green face the named speaker?", a side-by-side comparison instead of a hunt for a small
open mouth.

It runs only where it can help: one quoted line, no [offscreen], the gate's verdict PASS with faces_max >= 2 in
sync-N.json. CPU only (the sync venv: importing syncmeter re-execs into it), about 20 s a shot, cached in
<film>/.review/whospoke-N.{png,json} until the clip, its line or the portrait changes.

  whospoke.py <film-dir> <scene>...       one JSON line per scene: {"scene", "png" or null, "speaker", "why", ...}
  whospoke.py --clip C.mp4 --out O.png [--name NAME] [--portrait P.png]    one clip, no checks (tests)
"""
from __future__ import annotations
import hashlib, json, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import syncmeter as S  # noqa: E402  (re-execs into the sync venv when needed)
import numpy as np  # noqa: E402
import cv2  # noqa: E402
import dialogue as D  # noqa: E402  (rig/dialogue.py: the quoted lines and who says them)

COLS, TILE, MAX_ROWS, BAR = 4, 220, 3, 34
VERSION = 2   # in the cache key: a change to how the picture is made redraws it
GREEN, WHITE, GREY = (60, 220, 60), (255, 255, 255), (30, 30, 30)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def speaker_tracks(clip: Path):
    """Faces, voice and the speaking face exactly as syncmeter.measure finds them (keep this in step with it)."""
    p = S.probe(clip); fps = p["fps"]; H, W = p["h"], p["w"]
    frames = S.read_frames(clip, W, H); n = len(frames)
    voice = S.vocals16k(clip); env = S.envelope(voice, n, fps)
    db = 20 * np.log10(env + 1e-6); voiced = db > max(db.max() - 30, -50)
    if voiced.sum() < 0.5 * fps:
        return frames, fps, voiced, [], None
    tracks = S.track_faces(S.faces_per_frame(frames, fps))
    cands = []
    for t, tr in enumerate(tracks):
        d = S.syncnet_dists(S.crops(frames, tr, n), voice, fps)
        rows = np.arange(len(d))
        vo = voiced[:len(d)] | np.roll(voiced[:len(d)], 2) | np.roll(voiced[:len(d)], -2)
        _, conf, _ = S.offset_conf(d, rows[vo[:len(d)]] if vo[:len(d)].sum() >= 10 else None)
        det = np.array(sorted(tr))
        near = np.array([det[np.argmin(np.abs(det - i))] for i in range(n)])
        vis = np.array([abs(near[i] - i) <= 3 and tr[near[i]]["hshare"] * H >= S.THRESH["min_face_px"] for i in range(n)])
        cov = float(vis[voiced].mean()) if voiced.any() else 0.0
        xs = [(f["box"][0] + f["box"][2]) / 2 for f in tr.values()]
        cands.append({"track": t, "conf": float(conf), "coverage": cov, "tr": tr, "x": float(np.median(xs)),
                      "size": float(np.median([f["box"][3] - f["box"][1] for f in tr.values()]))})
    sp = max(cands, key=lambda c: c["conf"] * (0.3 + min(1.0, c["coverage"]))) if cands else None
    return frames, fps, voiced, cands, sp


def face_tile(rgb: np.ndarray, box, up: float = 0.12, wide: float = 0.85) -> np.ndarray:
    H, W = rgb.shape[:2]
    x0, y0, x1, y1 = box; fw, fh = x1 - x0, y1 - y0
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2 + up * fh, wide * max(fw, fh)
    a, b, c, e = int(max(0, cx - r)), int(max(0, cy - r)), int(min(W, cx + r)), int(min(H, cy + r))
    return cv2.resize(cv2.cvtColor(np.ascontiguousarray(rgb[b:e, a:c]), cv2.COLOR_RGB2BGR), (TILE, TILE))


def portrait_tile(path: Path) -> np.ndarray:
    """The portrait's face with its hair and headwear (cast portraits are often full length, the face small)."""
    bgr = cv2.imread(str(path))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    faces = S.faces_per_frame(rgb[None], 24.0, stride=1)[0]
    if not faces:
        h, w = bgr.shape[:2]; s = min(h, w)
        return cv2.resize(bgr[:s, (w - s) // 2:(w - s) // 2 + s], (TILE, TILE))
    f = max(faces, key=lambda d: d["box"][3] - d["box"][1])
    return face_tile(rgb, f["box"], up=-0.15, wide=1.25)


def text_fit(img: np.ndarray, txt: str, x: int, y: int, width: int, color=WHITE, scale: float = 0.62) -> None:
    while scale > 0.35 and cv2.getTextSize(txt, FONT, scale, 2)[0][0] > width:
        scale -= 0.04
    cv2.putText(img, txt, (x, y), FONT, scale, color, 2, cv2.LINE_AA)


def draw(frames, fps, voiced, cands, sp, out: Path, name: str | None, portrait: Path | None) -> dict:
    H = frames.shape[1]
    others = sorted((c for c in cands if c is not sp and c["coverage"] >= 0.2), key=lambda c: -c["size"])
    rows = sorted([sp] + others[:MAX_ROWS - 1], key=lambda c: c["x"])
    # moments spread over the spoken part, skipping LTX's first 0.4 s (pinned to the still) and the voice's ragged ends
    vidx = np.where(voiced)[0]
    vidx = vidx[vidx >= int(0.4 * fps)] if (vidx >= int(0.4 * fps)).sum() >= COLS else vidx
    lo, hi = int(np.percentile(vidx, 8)), int(np.percentile(vidx, 92))
    span = vidx[(vidx >= lo) & (vidx <= hi)]
    span = span if len(span) >= COLS else vidx
    moments = [int(span[int(k * (len(span) - 1) / (COLS - 1))]) for k in range(COLS)]
    letters = "ABC"; W0 = frames.shape[2]
    blocks, info = [], []
    for k, c in enumerate(rows):
        det = np.array(sorted(c["tr"]))
        tiles = []
        for i in moments:
            j = int(det[np.argmin(np.abs(det - i))])
            if abs(j - i) <= 6:
                t = face_tile(frames[j], c["tr"][j]["box"])
            else:
                t = np.full((TILE, TILE, 3), 60, np.uint8); text_fit(t, "not in frame", 10, TILE // 2, TILE - 20)
            text_fit(t, f"{i / fps:.1f} s", 8, 24, 80)
            if c is sp:
                cv2.rectangle(t, (2, 2), (TILE - 3, TILE - 3), GREEN, 6)
            tiles.append(t)
        pos = "left" if c["x"] < W0 / 3 else "right" if c["x"] > 2 * W0 / 3 else "middle"
        bar = np.full((BAR, TILE * COLS, 3), GREY, np.uint8)
        label = f"face {letters[k]} ({pos} of frame)" + (": THIS MOUTH MOVES WITH THE VOICE" if c is sp else "")
        text_fit(bar, label, 8, 24, TILE * COLS - 16, GREEN if c is sp else WHITE)
        blocks.append(np.vstack([bar, np.hstack(tiles)]))
        info.append({"face": letters[k], "pos": pos, "voice": c is sp, "conf": round(c["conf"], 2),
                     "face_px": round(c["size"]), "coverage": round(c["coverage"], 2)})
    grid = np.vstack(blocks)
    side = np.full((grid.shape[0], TILE, 3), GREY, np.uint8)
    text_fit(side, "the line belongs to:", 8, 24, TILE - 16)
    text_fit(side, name or "(see the line)", 8, 24 + BAR, TILE - 16, GREEN)
    if portrait is not None and portrait.exists():
        pt = portrait_tile(portrait); top = 2 * BAR
        h = min(TILE, side.shape[0] - top)
        if h > 40:
            side[top:top + h] = pt[:h]
        text_fit(side, "cast portrait", 8, min(side.shape[0] - 10, top + TILE + 24), TILE - 16)
    else:
        text_fit(side, "no portrait: match the", 8, 3 * BAR, TILE - 16)
        text_fit(side, "description in the line", 8, 4 * BAR, TILE - 16)
    img = np.hstack([side, np.full((grid.shape[0], 10, 3), 0, np.uint8), grid])
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)
    return {"rows": info, "moments_s": [round(i / fps, 2) for i in moments]}


def one_clip(clip: Path, out: Path, name: str | None = None, portrait: Path | None = None) -> dict:
    t0 = time.time()
    frames, fps, voiced, cands, sp = speaker_tracks(clip)
    if sp is None:
        return {"png": None, "why": "no voice or no face", "secs": round(time.time() - t0, 1)}
    if not [c for c in cands if c is not sp and c["coverage"] >= 0.2]:
        return {"png": None, "why": "one face on screen while the voice plays", "secs": round(time.time() - t0, 1)}
    res = draw(frames, fps, voiced, cands, sp, out, name, portrait)
    return {"png": str(out), **res, "secs": round(time.time() - t0, 1)}


def project_parts(project: Path):
    """SCENES and CAST of a project file, sourced the way rig/dialogue.py lint does."""
    r = subprocess.run(["zsh", "-c", 'SCENES=(); CAST=(); source "$1" >/dev/null 2>&1; '
                        'for s in "${SCENES[@]}"; do print -r -- "S:$s"; done; for c in "${CAST[@]}"; do print -r -- "C:$c"; done',
                        "_", str(project)], capture_output=True, text=True)
    scenes = [l[2:] for l in r.stdout.splitlines() if l.startswith("S:")]
    cast = {}
    for l in r.stdout.splitlines():
        if l.startswith("C:") and "|" in l:
            key, desc = l[2:].split("|", 1); cast[key.strip()] = desc.strip()
    return scenes, cast


def cast_name(key: str, desc: str) -> str:
    """"Marisol, a woman of about fifty, ..." -> Marisol; "a young woman of about twenty, ..." -> the key, capitalised."""
    first = desc.split(",")[0].strip()
    return first if first[:1].isupper() and len(first.split()) <= 3 else key.capitalize()


def for_scene(film: Path, n: int, scenes: list[str], cast: dict[str, str]) -> dict:
    if not 1 <= n <= len(scenes):
        return {"scene": n, "png": None, "why": "no such scene"}
    raw = scenes[n - 1]
    tokens = re.match(r"^((?:\[[^\]]*\]\s*)*)", raw).group(1)
    if "[offscreen]" in tokens:
        return {"scene": n, "png": None, "why": "an off-screen line"}
    text = D._TOKENS.sub("", raw)
    lines = D.quoted_lines(text)
    if len(lines) != 1:
        return {"scene": n, "png": None, "why": "no spoken line" if not lines else "an exchange (the gate checks each line's face)"}
    clip, sj = film / f"scene-{n}.mp4", film / f"sync-{n}.json"
    if not clip.exists() or not sj.exists():
        return {"scene": n, "png": None, "why": "no clip or no sync result"}
    g = json.loads(sj.read_text())
    if g.get("verdict") != "PASS":
        return {"scene": n, "png": None, "why": f"sync {g.get('verdict')}: the gate handles it"}
    if (g.get("faces_max") or 0) < 2:
        return {"scene": n, "png": None, "why": "one face"}
    speaker = (D.line_speakers(text) or [None])[0]
    if not speaker:
        # "he says": fall back to the shot's one [cast] character, else the one cast name the text mentions
        m = re.search(r"\[cast=([^\]]+)\]", tokens)
        keys = [k.strip() for k in m.group(1).split(",")] if m else []
        named = [k for k, desc in cast.items() if re.search(r"\b" + re.escape(desc.split(",")[0].strip()) + r"\b", text)]
        guess = keys if len(keys) == 1 else named if len(named) == 1 else []
        if not guess:
            # "she says" with one woman among the shot's cast (the-last-car: Marisol and Theo) means her
            m2 = list(D._LINE.finditer(text))
            clause = re.split(r"[.;:!?]\s", text[:m2[0].start()])[-1] if m2 else ""
            pron = (D._PRONOUN.search(clause).group(1).lower() if D._PRONOUN.search(clause) else "")
            pool = keys or named
            sexed = {"he": D._MALE, "she": D._FEMALE}.get(pron)
            if sexed:
                fits = [k for k in pool if k in cast and re.search(r"\b(?:" + sexed + r")\b", cast[k], re.I)]
                guess = fits if len(fits) == 1 else []
        if guess and guess[0] in cast:
            speaker = cast_name(guess[0], cast[guess[0]])
    portrait, key = None, None
    for k, desc in cast.items():
        if speaker and speaker.lower() in (k.lower(), desc.split(",")[0].strip().lower()):
            key = k; p = film / f"cast-{k}.png"; portrait = p if p.exists() else None
            break
    st = clip.stat()
    cache_key = hashlib.sha1(json.dumps([VERSION, st.st_size, st.st_mtime_ns, raw, str(portrait),
                                         portrait.stat().st_mtime_ns if portrait else 0]).encode()).hexdigest()[:16]
    png, meta = film / ".review" / f"whospoke-{n}.png", film / ".review" / f"whospoke-{n}.json"
    if png.exists() and meta.exists():
        old = json.loads(meta.read_text())
        if old.get("key") == cache_key:
            return old
    res = {"scene": n, "speaker": speaker, "cast": key, "portrait": bool(portrait), "line": lines[0],
           **one_clip(clip, png, speaker, portrait), "key": cache_key}
    if res.get("png") and res.get("rows"):
        # the gate's own pick is in sync-N.json; say so if this run's pick differs (it should not: same steps)
        res["gate_conf"] = g.get("conf")
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(res))
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--clip"]:
        opts = dict(zip(a[0::2], a[1::2]))
        r = one_clip(Path(opts["--clip"]).expanduser(), Path(opts["--out"]).expanduser(), opts.get("--name"),
                     Path(opts["--portrait"]).expanduser() if "--portrait" in opts else None)
        print(json.dumps(r)); sys.exit(0)
    film = Path(a[0]).expanduser()
    project = film / "project.txt"
    scenes, cast = project_parts(project) if project.exists() else ([], {})
    for s in a[1:]:
        try:
            r = for_scene(film, int(s), scenes, cast)
        except Exception as e:  # never break the review: no picture is the fallback
            r = {"scene": int(s), "png": None, "why": f"error: {e!r}"[:300]}
        print(json.dumps(r), flush=True)
