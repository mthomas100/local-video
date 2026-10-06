#!/usr/bin/env python3
"""backmeasure.py — measure every dialogue shot of a finished film three ways with rig/sync/syncmeter.py (2026-09-27).

  backmeasure.py <film> [--out rows.jsonl]

For each scene whose line has a spoken line:
  raw     ~/Videos/vidgen/<film>/scene-N.mp4 (the take in the film)
  final   the same shot's window cut out of the stitched <film>.mp4 (frame-accurate re-encode of both streams from the
          shot's start; the start is the sum of the earlier clips' container durations, which is how the concat
          demuxer lays them end to end). raw vs final = the pipeline's own offset (root cause P1), per shot along the
          film (P2).
  takes   every earlier take in redo-*/scene-N.mp4 (the model's spread on the same line: M1/M3 vs luck)
One JSON line per measurement: {"film", "scene", "kind", "file", "start_s", ...meter fields}.
"""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import syncmeter  # noqa: E402
from gate import scene_texts, tokens_and_line  # noqa: E402
from dialogue import quoted_lines  # noqa: E402

VIDEOS = Path.home() / "Videos/vidgen"


def fmt_dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout.strip())


def main(film: str, out: Path | None) -> None:
    d = VIDEOS / film
    texts = scene_texts(d)
    starts, t = {}, 0.0
    for n in range(1, len(texts) + 1):
        starts[n] = t
        t += fmt_dur(d / f"scene-{n}.mp4")
    final = d / f"{film}.mp4"
    rows = []
    with tempfile.TemporaryDirectory() as td:
        # The final cut is measured as a player plays it (2026-10-03): the picture by its timestamps and the sound
        # decoded back to back, the way QuickTime/iOS/AVFoundation play AAC. Cutting the film itself with -ss
        # re-anchors sound and picture at every window, which hid a drift of up to 2.2 s through four films
        # (docs/data/sync-drift/README.md).
        if final.exists():
            pv = Path(td) / "player-view.mp4"
            wav = Path(td) / "contiguous.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-vn", "-ac", "1", "-ar", "48000", str(wav)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(pv)], check=True)
            final = pv
        for n, text in enumerate(texts, 1):
            _, body = tokens_and_line(text)
            lines = quoted_lines(body)
            if not lines: continue
            line = " ".join(lines)
            jobs = [("raw", d / f"scene-{n}.mp4", None)]
            if final.exists():
                w = Path(td) / f"final-{n}.mp4"
                dur = fmt_dur(d / f"scene-{n}.mp4")
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-ss", f"{starts[n]:.3f}", "-t",
                                f"{dur:.3f}", "-c:v", "libx264", "-crf", "16", "-c:a", "aac", "-b:a", "192k", str(w)],
                               check=True)
                jobs.append(("final", w, starts[n]))
            for tk in sorted(d.glob(f"redo-*/scene-{n}.mp4")):
                jobs.append((f"take:{tk.parent.name}", tk, None))
            # the gate's retakes (2026-09-27): takes/ for the current round, redo-*/ for earlier rounds
            for tk in sorted(d.glob(f"redo-*/scene-{n}-try*.mp4")) + sorted(d.glob(f"takes/scene-{n}-try*.mp4")):
                jobs.append((f"take:{tk.parent.name}/{tk.stem.split('-')[-1]}", tk, None))
            for kind, f, st in jobs:
                # an earlier take is measured against its own line (its sidecar's prompt), not today's words
                side = f.with_suffix(".json")
                ql = quoted_lines(json.loads(side.read_text()).get("prompt", "")) if kind.startswith("take:") and side.exists() else []
                try: r = syncmeter.measure(f, " ".join(ql) if ql else line, one_line=len(ql or lines) == 1)
                except Exception as e: r = {"error": repr(e)}
                r.update({"film": film, "scene": n, "kind": kind, "file": str(f), "start_s": st, "line": " ".join(ql) if ql else line})
                rows.append(r)
                print(json.dumps(r), flush=True)
                print(f"# {film} {n} {kind}: {syncmeter.line_of(str(n), r) if 'verdict' in r else r.get('error')}",
                      file=sys.stderr, flush=True)
    if out: out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    o = Path(a[a.index("--out") + 1]) if "--out" in a else None
    main(a[0], o)
