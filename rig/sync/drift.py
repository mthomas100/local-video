#!/usr/bin/env python3
"""drift.py — film-level A/V drift check of a stitched film (2026-10-03, iteration 6).

Why: the human sees dialogue in sync at the start of a film and drifting later. Per-shot sync meters can't see that,
because they cut each window with `-ss`, which re-anchors audio and video at the window's start. Players don't:
QuickTime, iOS and the AVFoundation export play AAC samples back to back and ignore timestamp gaps. Measured on Warm
(2026-09-28): each of its 24 joins left a ~90 ms gap in the audio timestamps, so the contiguous audio is 2.16 s
shorter than the film. Played back, the voice runs ~90 ms earlier after every cut, ~2.1 s early by the end.

What it does, from timestamps only (ffprobe, no decoding of pictures):
  - lists every gap or overlap in the audio and video packet timestamps (more than half a packet off the cadence);
  - the drift a contiguous player shows at each audio gap: the sum of the audio gaps so far (negative = voice early);
  - the contiguous audio duration (samples decoded) against the video duration.
Exit 0 when the worst drift is within --tol-ms (default 20 ms, under the 45 ms audio-early detectability threshold
of ITU-R BT.1359), else 1. `--json` prints one JSON object.

Usage: rig/sync/drift.py <film.mp4> [--tol-ms 20] [--json]
"""
import json, subprocess, sys


def packets(path, stream):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries",
                          "packet=pts_time,duration_time", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.strip().strip(",").split(",")
        if not parts or parts[0] in ("", "N/A"):
            continue
        rows.append((float(parts[0]), float(parts[1]) if len(parts) > 1 and parts[1] not in ("", "N/A") else None))
    rows.sort()
    return rows


def gaps(rows):
    """(at, gap_s) for every jump in the timestamps beyond half the typical packet duration."""
    if len(rows) < 3:
        return [], 0.0
    deltas = sorted(b[0] - a[0] for a, b in zip(rows, rows[1:]))
    step = deltas[len(deltas) // 2]          # the cadence: the median packet spacing
    out = []
    for a, b in zip(rows, rows[1:]):
        d = b[0] - a[0] - step
        if abs(d) > step / 2:
            out.append((round(b[0], 3), round(d, 4)))
    return out, step


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(2)
    path = args[0]
    tol = float(args[args.index("--tol-ms") + 1]) if "--tol-ms" in args else 20.0
    a, v = packets(path, "a:0"), packets(path, "v:0")
    if not a or not v:
        print(json.dumps({"film": path, "error": "needs one audio and one video stream"})); sys.exit(1)
    ag, astep = gaps(a)
    vg, vstep = gaps(v)
    v_dur = v[-1][0] + (v[-1][1] or vstep) - v[0][0]
    a_contig = len(a) * astep                     # what a player that plays samples back to back hears
    a_span = a[-1][0] + (a[-1][1] or astep) - a[0][0]
    drift, run = [], 0.0
    for at, g in ag:
        run += g
        drift.append((at, round(-run * 1000)))   # ms; negative = the voice plays early
    worst = max((abs(d) for _, d in drift), default=0)
    res = {"film": path, "video_s": round(v_dur, 3), "audio_timeline_s": round(a_span, 3),
           "audio_contiguous_s": round(a_contig, 3), "audio_gaps": len(ag), "video_gaps": len(vg),
           "drift_ms_at_gaps": drift, "worst_drift_ms": worst, "tol_ms": tol,
           "verdict": "OK" if worst <= tol and abs(a_contig - v_dur) * 1000 <= max(tol, 1000 * vstep) else "DRIFT"}
    if "--json" in args:
        print(json.dumps(res))
    else:
        print(f"drift {res['verdict']}: video {res['video_s']} s, audio {res['audio_contiguous_s']} s played back to "
              f"back ({res['audio_timeline_s']} s by timestamps); {len(ag)} audio and {len(vg)} video timestamp gaps; "
              f"worst drift {worst} ms (tolerance {tol:g} ms)")
        for at, d in drift:
            print(f"  at {at:8.3f} s: voice {abs(d)} ms {'early' if d < 0 else 'late'}")
    sys.exit(0 if res["verdict"] == "OK" else 1)


if __name__ == "__main__":
    main()
