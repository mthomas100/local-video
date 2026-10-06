#!/usr/bin/env python3
"""mouthing.py — silent articulation: does the speaker's mouth talk where there is no voice? (2026-09-27, iteration 5)

A viewer reads lips moving with no sound as "out of sync" even when the voiced part is in sync. This measures, for the
speaker (the face track syncmeter.py would pick), the seconds of lip MOVEMENT outside the voice (150 ms margins, the first
0.4 s skipped: in LTX clips it is pinned to the still), counting a frame when the smoothed lip speed is over half the
median speed while speaking. A lip opening held still (a smile after the line) does not count. Also: the longest voiced
run with the lips still (voice without mouth). Local, CPU, same instruments as syncmeter.py (reported, not in the gate).

Calibration (rig/sync/CALIBRATION.md §8): real in-sync RAVDESS 0.20-0.53 s; every clip the gate passes (liminal-clowns,
both halloween films, the phase-2 A/B) 0.00-0.75 s; planted mutes of 1.5-2.5 s of a line read 0.83-2.29 s; clips the
gate already fails 0.96-5.42 s. So far the gate's confidence bar already catches silent talking.

  mouthing.py <clip.mp4>...     one JSON line per clip: art_s, art_run_s, art_share, voiced_still_run_s, conf, offset_ms
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import syncmeter as S  # noqa: E402  (re-execs into the sync venv when needed)
import numpy as np  # noqa: E402


def runmax(b):
    run = m = 0
    for x in b: run = run + 1 if x else 0; m = max(m, run)
    return m

def explore(clip: Path) -> dict:
    p = S.probe(clip); fps = p["fps"]
    frames = S.read_frames(clip, p["w"], p["h"]); n = len(frames)
    voice = S.vocals16k(clip); env = S.envelope(voice, n, fps)
    db = 20 * np.log10(env + 1e-6); voiced = db > max(db.max() - 30, -50)
    per = S.faces_per_frame(frames, fps); tracks = S.track_faces(per)
    best = None
    for tr in tracks:
        d = S.syncnet_dists(S.crops(frames, tr, n), voice, fps)
        rows = np.arange(len(d)); vo = voiced[:len(d)] | np.roll(voiced[:len(d)], 2) | np.roll(voiced[:len(d)], -2)
        off, conf, _ = S.offset_conf(d, rows[vo[:len(d)]] if vo[:len(d)].sum() >= 10 else None)
        cov = np.mean([any(abs(i - j) <= 3 for j in tr) for i in np.where(voiced)[0]]) if voiced.any() else 0
        if best is None or conf * (0.3 + cov) > best[0] * (0.3 + best[3]): best = (conf, off, tr, cov)
    if best is None: return {"clip": str(clip), "err": "no face"}
    conf, off, tr, cov = best
    idx = np.array(sorted(i for i in tr if tr[i]["open"] is not None))
    if len(idx) < 12: return {"clip": str(clip), "err": "few lips"}
    mo = np.interp(np.arange(n), idx, [tr[i]["open"] for i in idx])
    seen = np.zeros(n, bool); seen[[i for i in range(n) if any(abs(i - j) <= 3 for j in idx)]] = True
    k = int(round(0.15 * fps))
    near = np.convolve(voiced.astype(float), np.ones(2 * k + 1), "same") > 0
    far = ~near & seen; far[: int(0.4 * fps)] = False
    mot = np.convolve(np.abs(np.diff(mo, prepend=mo[0])), np.ones(5) / 5, "same")   # smoothed lip speed
    spk = float(np.median(mot[voiced & seen])) if (voiced & seen).any() else 0.0
    out = {"clip": clip.parent.name + "/" + clip.name, "conf": round(conf, 2), "offset_ms": round(off * 1000 / fps),
           "voiced_s": round(voiced.sum() / fps, 2), "silent_s": round(far.sum() / fps, 2)}
    if spk > 0:
        art = far & (mot > 0.5 * spk)
        out["art_run_s"] = round(runmax(art) / fps, 2)
        out["art_share"] = round(float(art.sum() / max(1, far.sum())), 2)
        out["art_s"] = round(art.sum() / fps, 2)
        still = voiced & seen & (mot < 0.2 * spk)
        out["voiced_still_run_s"] = round(runmax(still) / fps, 2)
    return out

for c in sys.argv[1:]:
    try: print(json.dumps(explore(Path(c).expanduser())), flush=True)
    except Exception as e: print(json.dumps({"clip": c, "err": repr(e)[:200]}), flush=True)
