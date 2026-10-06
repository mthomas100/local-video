#!/usr/bin/env python3
"""lipsync.py — how well a clip's mouth movement follows its own speech (2026-09-27). CPU only.

STATUS 2026-09-27 12:40 — UNCALIBRATED, DISPUTED. It reported 9 of 10 liminal-clowns dialogue shots in sync; the human
watched the film and found many out of sync. On planted controls (rig/sync/make_controls.py, shot 3) its best lag
recovers shifts within a frame, but its "in sync" rule (corr0 >= 0.4) passes a 400 ms offset. Replace or calibrate it
per `docs/dialogue-sync.md`; the stitch nudge below is off unless LIPSYNC_NUDGE=1.

The human saw dialogue whose mouth movement did not match the words. This meter measures it per clip:
  mouth   the largest face's inner-lip opening per frame (macOS Vision landmarks, bin/mouth.swift)
  voice   the speech-band loudness of the clip's audio (200-3500 Hz RMS), one value per video frame
  corr0   Pearson correlation of mouth and voice at zero lag (lip sync: higher is better; a talking head in sync is
          typically 0.3-0.6, unrelated series about 0)
  best    the lag in ms where the correlation peaks, within +-500 ms, and its value (a large |lag| = offset audio)
  face    the fraction of frames with a detected face (low = the speaker is too small, turned away or off screen)
  talkmove  mouth motion while the voice is loud, divided by mouth motion while it is quiet (>1: the mouth moves when
          someone speaks)
The stitched film is checked separately (clip audio vs video start and length); a clip-level meter says whether the
generation itself is in sync.

  lipsync.py <clip.mp4>...            one JSON line per clip
  lipsync.py nudge <clip.mp4> <line>  the audio shift in ms the stitch applies to this clip (0 = none), and why on stderr

The nudge (2026-09-27): in the flagged dialogue shots of the last three films the mouth LED the voice by 330-500 ms
(scene 8 of halloween-clowns-sf-portrait: the mouth opens, then the words come as it closes). When a clip has a quoted
line, a face in most frames, and its mouth matches its voice clearly better at an offset (best >= 0.45, at least 0.15
above the zero-lag correlation, |lag| >= 100 ms), story.sh shifts that clip's audio by the lag in the stitched film. The
rendered clip is never changed.
"""
from __future__ import annotations
import json, os, re, subprocess, sys, tempfile
from pathlib import Path
try:
    import numpy as np
except ImportError:
    venv = Path.home() / "repos/ltx-2-mlx/.venv/bin/python"
    if os.environ.get("LIPSYNC_REEXEC") != "1" and venv.exists():
        os.environ["LIPSYNC_REEXEC"] = "1"; os.execv(str(venv), [str(venv), __file__, *sys.argv[1:]])
    raise
REPO = Path(__file__).resolve().parents[2]
MOUTH = Path.home() / ".cache/local-video/mouth"

def mouth_bin() -> Path:
    src = REPO / "bin/mouth.swift"
    if not MOUTH.exists() or MOUTH.stat().st_mtime < src.stat().st_mtime:
        MOUTH.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", "-o", str(MOUTH), str(src)], check=True, capture_output=True)
    return MOUTH

def fps_of(clip: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", str(clip)], capture_output=True, text=True).stdout.strip()
    a, b = (r.split("/") + ["1"])[:2]
    return float(a) / float(b or 1)

def measure(clip: Path) -> dict:
    fps = fps_of(clip)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", "scale=640:-2", f"{td}/f-%05d.png"], check=True)
        frames = sorted(Path(td).glob("f-*.png"))
        out = subprocess.run([str(mouth_bin()), *map(str, frames)], capture_output=True, text=True).stdout
        m = [json.loads(l)["open"] for l in out.splitlines() if l.strip()]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000",
                              "-af", "highpass=f=200,lowpass=f=3500", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    n = len(m)
    hop = 16000 / fps
    voice = np.array([np.sqrt(np.mean(a[int(i * hop):int((i + 1) * hop)] ** 2)) if int(i * hop) < len(a) else 0.0 for i in range(n)])
    have = np.array([x is not None for x in m])
    face = float(have.mean()) if n else 0.0
    res = {"clip": str(clip), "frames": n, "fps": round(fps, 2), "face": round(face, 2)}
    if have.sum() < max(12, n // 4) or voice.max() <= 0:
        return {**res, "corr0": None, "best_lag_ms": None, "best": None, "talkmove": None, "note": "too few face frames or no audio"}
    mo = np.array([x if x is not None else np.nan for x in m], dtype=float)
    idx = np.arange(n)
    mo = np.interp(idx, idx[have], mo[have])          # bridge short dropouts
    v = np.log(voice + 1e-4)
    def corr(lag: int) -> float:
        if lag >= 0: x, y = mo[lag:], v[:n - lag]       # positive lag: the mouth follows the voice
        else: x, y = mo[:n + lag], v[-lag:]
        ok = have[lag:] if lag >= 0 else have[:n + lag]
        x, y = x[ok], y[ok]
        if len(x) < 10 or x.std() == 0 or y.std() == 0: return 0.0
        return float(np.corrcoef(x, y)[0, 1])
    lags = range(-int(0.5 * fps), int(0.5 * fps) + 1)
    cs = {l: corr(l) for l in lags}
    best = max(cs, key=cs.get)
    loud = v > np.percentile(v, 60)
    motion = np.abs(np.diff(mo, prepend=mo[0]))
    q = motion[~loud].mean() if (~loud).any() else 0
    talkmove = float(motion[loud].mean() / q) if q > 0 else None
    return {**res, "corr0": round(cs[0], 3), "best_lag_ms": round(best * 1000 / fps), "best": round(cs[best], 3),
            "talkmove": round(talkmove, 2) if talkmove else None}

sys.path.insert(0, str(REPO / "rig"))
from dialogue import has_line  # noqa: E402  (one definition of a spoken line, shared with bin/still and the pre-check)


def nudge(clip: Path, line: str) -> int:
    if not has_line(line):
        print("no quoted line", file=sys.stderr); return 0
    m = measure(clip)
    print(json.dumps(m), file=sys.stderr)
    if (m.get("face") or 0) < 0.6 or m.get("best") is None or m.get("corr0") is None:
        return 0
    if m["best"] >= 0.45 and m["best"] - m["corr0"] >= 0.15 and abs(m["best_lag_ms"]) >= 100:
        return int(m["best_lag_ms"])
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["nudge"]:
        print(nudge(Path(sys.argv[2]).expanduser(), sys.argv[3])); sys.exit(0)
    for c in sys.argv[1:]:
        try: print(json.dumps(measure(Path(c).expanduser())), flush=True)
        except Exception as e: print(json.dumps({"clip": c, "error": str(e)}), flush=True)
