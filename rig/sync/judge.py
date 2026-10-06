#!/usr/bin/env python3
"""judge.py — a local multimodal judge that watches AND hears a clip (2026-09-27, iteration 5). GPU (MLX): run it only
when no render or director model is on the GPU.

Qwen3-Omni-30B-A3B-Instruct (8-bit MLX, mlx-vlm) is given the clip's frames and its audio together
(use_audio_in_video: the model interleaves them by time) and asked, as a viewer would be, whether the mouth matches the
voice and how the line is delivered. It stands in for a viewer only after it passes the same planted controls as every
other instrument (rig/sync/CALIBRATION.md §7): it must tell an in-sync take from +200 ms and from a swapped voice.

  judge.py <clip.mp4> [--line "the asked words"] [--note "want / verb / beat"]   one JSON line per clip
"""
from __future__ import annotations
import json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

VENV = Path.home() / ".cache/local-video/omni-venv/bin/python"
try:
    import mlx.core as mx
    from mlx_vlm import load
    from mlx_vlm.generate import generate
except ImportError:
    if os.environ.get("JUDGE_REEXEC") != "1" and VENV.exists():
        os.environ["JUDGE_REEXEC"] = "1"; os.execv(str(VENV), [str(VENV), os.path.abspath(sys.argv[0]), *sys.argv[1:]])
    raise

MODEL = "mlx-community/Qwen3-Omni-30B-A3B-Instruct-8bit"
PROMPT = """You are a film editor checking dialogue. Watch this clip and listen to its audio together.
{line}
Answer ONLY with one JSON object, no other text:
{{"speaker_visible": true/false,
  "lip_sync": "in sync" | "voice early" | "voice late" | "mouth does not form the words" | "mouth still while voice plays" | "cannot see the mouth",
  "sync_confidence": 1-5,
  "delivery": 1-5,
  "delivery_tag": "flat" | "awkward" | "overacted" | "wrong emotion" | "right",
  "emotion_heard": "<one or two words>",
  "why": "<one short sentence>"}}
"voice early" means the sound of a word comes before the lips make it; "voice late" means after."""

_m = None


def model():
    global _m
    if _m is None:
        _m = load(MODEL)
    return _m


def judge(clip: Path, line: str | None = None, note: str | None = None, fps: float = 4.0) -> dict:
    m, proc = model()
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
        vid = Path(td) / "v.mp4"   # a light copy: 448 px wide, fps frames per second, for the vision tower
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"fps={fps},scale=448:-2", "-an", str(vid)],
                       check=True)
        ask = f"The line asked for: '{line}'." if line else ""
        if note: ask += f" The director's note for the delivery: {note}."
        conv = [{"role": "user", "content": [{"type": "video", "video": str(vid)}, {"type": "audio", "audio": str(wav)},
                                              {"type": "text", "text": PROMPT.format(line=ask)}]}]
        prompt = proc.apply_chat_template(conv, add_generation_prompt=True, tokenize=False)
        out = generate(m, proc, prompt, video=[str(vid)], audio=[str(wav)], max_tokens=300, temperature=0.0,
                       use_audio_in_video=False, verbose=False)
    text = getattr(out, "text", out if isinstance(out, str) else str(out))
    mx.clear_cache()
    mm = re.search(r"\{.*\}", text, re.S)
    try: r = json.loads(mm.group(0)) if mm else {"raw": text}
    except json.JSONDecodeError: r = {"raw": text}
    r.update({"clip": str(clip), "secs": round(time.time() - t0, 1), "judge": MODEL})
    return r


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("clips", nargs="+"); ap.add_argument("--line"); ap.add_argument("--note")
    a = ap.parse_args()
    for c in a.clips:
        try: r = judge(Path(c).expanduser(), a.line, a.note)
        except Exception as e: r = {"clip": c, "error": repr(e)[:400]}
        print(json.dumps(r), flush=True)
