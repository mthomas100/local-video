#!/usr/bin/env python3
"""make_controls.py — planted-truth controls for any lip-sync meter (2026-09-27). CPU only (ffmpeg + numpy).

Why: on 2026-09-27 the human watched liminal-clowns and saw many dialogue shots out of sync, while
rig/audit/lipsync.py had passed 9 of 10. That meter had only ever been checked against itself. A meter is trusted
only after it (1) recovers offsets we planted ourselves, within one frame, and (2) rejects a clip whose audio belongs
to another clip. This script makes those controls from real rig footage; the truth is in manifest.json.

  make_controls.py <clip.mp4> <other-clip.mp4> <out-dir> [shifts_ms ...]

  shift_ms > 0: the audio is DELAYED (the voice comes after the mouth; audio lags video)
  shift_ms < 0: the audio is ADVANCED (the voice comes before the mouth; audio leads video)
  The video stream is copied untouched; the clip length is kept (the audio is trimmed or padded with silence).
  swap.mp4 = this clip's video with <other-clip>'s audio (same length): a correct meter must call it out of sync.
  hidden.mp4 = the picture covered (a meter must say UNMEASURABLE); frozen.mp4 = the first frame held under the voice
  (a meter must FAIL it: the mouth does not move).

The script checks its own truth: it cross-correlates each control's audio with the source audio and records the
measured shift next to the planted one (they must agree to within a millisecond or two).
"""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
try:
    import numpy as np
except ImportError:
    venv = Path.home() / "repos/ltx-2-mlx/.venv/bin/python"
    if os.environ.get("CONTROLS_REEXEC") != "1" and venv.exists():
        os.environ["CONTROLS_REEXEC"] = "1"; os.execv(str(venv), [str(venv), __file__, *sys.argv[1:]])
    raise

DEFAULT_SHIFTS = [-400, -200, -120, -80, -40, 0, 40, 80, 120, 200, 400]
SR = 16000


def duration(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True).stdout.strip())


def pcm(p: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def measured_shift_ms(src: np.ndarray, ctl: np.ndarray, max_ms: int = 600) -> float:
    """Lag (ms) that best aligns ctl to src; positive = ctl is later (delayed)."""
    m = int(max_ms * SR / 1000)
    n = min(len(src), len(ctl))
    s, c = src[:n], ctl[:n]
    best, arg = -1.0, 0
    for lag in range(-m, m + 1, 8):  # 0.5 ms steps
        if lag >= 0: a, b = s[:n - lag], c[lag:]
        else: a, b = s[-lag:], c[:n + lag]
        v = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        if v > best: best, arg = v, lag
    return round(arg * 1000 / SR, 1)


def make(clip: Path, other: Path, out: Path, shifts: list[int]) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    d = duration(clip)
    src = pcm(clip)
    rows = []
    for s in shifts:
        name = f"shift{'+' if s > 0 else ''}{s}ms.mp4"
        if s > 0: af = f"adelay={s}:all=1,atrim=end={d}"
        elif s < 0: af = f"atrim=start={-s / 1000},asetpts=PTS-STARTPTS,apad=pad_dur={-s / 1000},atrim=end={d}"
        else: af = f"atrim=end={d}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-c:v", "copy", "-af", af, "-c:a", "aac",
                        "-b:a", "192k", str(out / name)], check=True)
        rows.append({"file": name, "kind": "shift", "planted_ms": s, "check_ms": measured_shift_ms(src, pcm(out / name))})
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-i", str(other), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", f"apad,atrim=end={d}", "-c:a", "aac", "-b:a", "192k", str(out / "swap.mp4")],
                   check=True)
    rows.append({"file": "swap.mp4", "kind": "swap", "planted_ms": None, "audio_from": str(other)})
    # 2026-09-27 (iteration 5): a meter must also say UNMEASURABLE when it cannot see a face, and FAIL a mouth that
    # does not move while the voice plays. hidden.mp4 = the frame covered but for a thin border (no face to read);
    # frozen.mp4 = the first frame held for the whole clip under the clip's own voice.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vf",
                    "drawbox=x=iw*0.05:y=ih*0.05:w=iw*0.9:h=ih*0.9:color=gray:t=fill", "-c:v", "libx264", "-crf", "18",
                    "-c:a", "copy", str(out / "hidden.mp4")], check=True)
    rows.append({"file": "hidden.mp4", "kind": "hidden", "planted_ms": None})
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vf", "select=eq(n\\,0),loop=-1:1:0,setpts=N/FRAME_RATE/TB",
                    "-frames:v", str(int(round(d * 24))), "-r", "24", "-c:v", "libx264", "-crf", "18", "-map", "0:v",
                    "-map", "0:a", "-c:a", "copy", "-shortest", str(out / "frozen.mp4")], check=True)
    rows.append({"file": "frozen.mp4", "kind": "frozen", "planted_ms": None})
    man = {"source": str(clip), "other": str(other), "duration_s": d,
           "convention": "planted_ms > 0: audio delayed (lags video); < 0: audio advanced (leads video)",
           "controls": rows}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(2)
    shifts = [int(x) for x in sys.argv[4:]] or DEFAULT_SHIFTS
    m = make(Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser(), Path(sys.argv[3]).expanduser(), shifts)
    for r in m["controls"]:
        print(json.dumps(r))
