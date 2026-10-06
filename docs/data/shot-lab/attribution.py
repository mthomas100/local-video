#!/usr/bin/env python3
"""attribution.py <clip.mp4> --lines "line one" "line two" ... [--json] — whose mouth says which line (shot lab,
2026-10-03).

Why: LTX's audio-video attention carries time, not place (the LTX-2 report), so in a shot with two people the
voice can land in the wrong mouth, or in both (MTAVG-Bench: LTX-2.3 put the line in the right speaker's mouth in
24% of multi-speaker clips). Meter v3 picks the face that best follows the WHOLE voice; that cannot say whether
line 1 came from the left person and line 2 from the right one. This script splits the voice by line (forced
alignment of all the lines in order) and, for each line's span, scores every face track with SyncNet on just those
frames.

Output per line: its time span, and per track: screen position (x of the box centre, 0 = left edge, 1 = right),
median face height in px, SyncNet confidence and offset on that span. The line's speaker is the track with the
highest confidence whose offset is not at the search edge; "also" lists other tracks above the confidence bar at
an offset within 2 frames of the speaker's (a second mouth saying the same line).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path.home() / "repos/local-video/rig/sync"))
import syncmeter as sm


def strip(frames, tracks, picks, out: Path) -> None:
    """Full frames (scaled to 240 px wide), the line's speaker boxed green and any second mouth red."""
    import cv2
    tiles = []
    for i, green, reds in picks:
        f = cv2.cvtColor(frames[i], cv2.COLOR_RGB2BGR).copy()
        for t, col in [(green, (0, 255, 0))] + [(r, (0, 0, 255)) for r in reds]:
            if t is None: continue
            near = min(tracks[t], key=lambda j: abs(j - i))
            if abs(near - i) > 6: continue
            x0, y0, x1, y1 = map(int, tracks[t][near]["box"])
            cv2.rectangle(f, (x0, y0), (x1, y1), col, max(2, f.shape[1] // 200))
        tiles.append(cv2.resize(f, (240, int(240 * f.shape[0] / f.shape[1]))))
    if tiles:
        h = max(t.shape[0] for t in tiles)
        cv2.imwrite(str(out), np.hstack([cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 4, cv2.BORDER_CONSTANT) for t in tiles]))


def attribute(clip: Path, lines: list[str], strip_out: Path | None = None) -> dict:
    p = sm.probe(clip); fps = p["fps"]
    frames = sm.read_frames(clip, p["w"], p["h"]); n = len(frames)
    voice = sm.vocals16k(clip)
    tracks = sm.track_faces(sm.faces_per_frame(frames, fps))
    words = sm.align(voice, " ".join(lines))
    counts = [len(l.split()) for l in lines]
    out = {"clip": str(clip), "fps": fps, "detect_scale": sm._last_scale, "tracks": [], "lines": []}
    dists = []
    for t, tr in enumerate(tracks):
        d = sm.syncnet_dists(sm.crops(frames, tr, n), voice, fps)
        dists.append(d)
        xs = [((f["box"][0] + f["box"][2]) / 2) / p["w"] for f in tr.values()]
        out["tracks"].append({"track": t, "x": round(float(np.median(xs)), 2),
                              "face_px": round(float(np.median([f["hshare"] for f in tr.values()])) * p["h"]),
                              "frames": len(tr)})
    if not words or len(words) < sum(counts) * 0.6:
        out["error"] = f"forced alignment found {len(words) if words else 0} of {sum(counts)} words"
        return out
    i = 0
    for li, (line, c) in enumerate(zip(lines, counts)):
        ws = words[i:i + c]; i += c
        if not ws: continue
        t0, t1 = ws[0]["start"], ws[-1]["end"]
        rows = np.arange(max(0, int(t0 * fps) - 2), min(n - 5, int(t1 * fps) + 3))
        per = []
        for t, d in enumerate(dists):
            rr = rows[rows < len(d)]
            if len(rr) < 6: continue
            off, conf, _ = sm.offset_conf(d, rr)
            per.append({"track": t, "x": out["tracks"][t]["x"], "conf": round(conf, 2),
                        "offset_ms": round(off * 1000 / fps), "edge": abs(off) >= sm.THRESH["edge_frames"]})
        ok = [q for q in per if not q["edge"]]
        sp = max(ok, key=lambda q: q["conf"]) if ok else None
        def together(a: int, b: int) -> float:
            """share of this line's frames in which both tracks have a face within 3 frames (both on screen)"""
            fa, fb = np.array(sorted(tracks[a])), np.array(sorted(tracks[b]))
            near = lambda f, i: len(f) and np.min(np.abs(f - i)) <= 3
            return float(np.mean([near(fa, i) and near(fb, i) for i in rows])) if len(rows) else 0.0
        also = [dict(q, together=round(together(sp["track"], q["track"]), 2)) for q in ok
                if sp and q is not sp and q["conf"] >= sm.THRESH["min_conf"]
                and abs(q["offset_ms"] - sp["offset_ms"]) <= 2 * 1000 / fps]
        also = [q for q in also if q["together"] >= 0.3]   # the same person after a cut is a new track, not a 2nd mouth
        out["lines"].append({"line": line, "start_s": round(t0, 2), "end_s": round(t1, 2), "per_track": per,
                             "speaker": sp, "also": also, "_rows": rows})
    if strip_out:
        picks = []
        for L in out["lines"]:
            r = L["_rows"]
            for k in (0.2, 0.5, 0.8):
                picks.append((int(r[int(k * (len(r) - 1))]), L["speaker"]["track"] if L["speaker"] else None,
                              [q["track"] for q in L["also"]]))
        strip(frames, tracks, picks, strip_out)
    for L in out["lines"]: L.pop("_rows", None)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("clip"); ap.add_argument("--lines", nargs="+", required=True)
    ap.add_argument("--strip")
    a = ap.parse_args()
    print(json.dumps(attribute(Path(a.clip), a.lines, Path(a.strip) if a.strip else None)))
