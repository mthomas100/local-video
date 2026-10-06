#!/usr/bin/env python3
"""tts.py — a character's line as a WAV, acted, for audio-first dialogue (2026-09-27, iteration 5). Local.

Qwen3-TTS 1.7B VoiceDesign on MLX (mlx-audio, ~/repos/mlx-audio/.venv; the GPU, so only between renders: on the CPU
the PyTorch build took over 10 minutes for one line, 2026-09-27) speaks each part of the line with instruct = the character's fixed voice (persona) + this part's delivery (performance.md §6).
The parts are laid on a timeline: a lead-in beat (so speech never starts inside the first, image-pinned latent:
root cause M4), the given pauses between parts, silence to the clip length. The output is what `ltx-2-mlx a2v` is
driven by, and what the final clip's voice track is.

  tts.py -o line.wav --persona "a man of about forty, a low rough baritone" --secs 8.04 [--lead 0.6] [--seed 7]
         --part "Don't look too long." "low and quiet, a warning" [--pause 0.7 --part "..." "..."]
Prints JSON: parts with start/end seconds, total speech seconds, and whether it fits.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

VENV = Path.home() / "repos/mlx-audio/.venv/bin/python"
try:
    import numpy as np, soundfile as sf
    import mlx.core as mx
    from mlx_audio.tts.utils import load_model
except ImportError:
    if os.environ.get("TTS_REEXEC") != "1" and VENV.exists():
        os.environ["TTS_REEXEC"] = "1"; os.execv(str(VENV), [str(VENV), __file__, *sys.argv[1:]])
    raise

MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
_tts = None


def model(device: str = "mlx"):
    global _tts
    if _tts is None:
        _tts = load_model(MODEL)
    return _tts


def say(text: str, instruct: str, seed: int) -> tuple[np.ndarray, int]:
    mx.random.seed(seed)
    parts, sr = [], 24000
    for r in model().generate(text, instruct=instruct, lang_code="english", max_tokens=int(len(text) * 1.6) + 40):
        parts.append(np.asarray(r.audio, dtype=np.float32)); sr = r.sample_rate
    mx.clear_cache()
    return (np.concatenate(parts) if parts else np.zeros(0, np.float32)), sr


def trim(w: np.ndarray, sr: int, db: float = -40) -> np.ndarray:
    """Cut leading and trailing silence (the model pads), keeping 30 ms."""
    env = np.abs(w)
    thr = np.max(env) * 10 ** (db / 20)
    idx = np.where(env > thr)[0]
    if not len(idx): return w
    k = int(0.03 * sr)
    return w[max(0, idx[0] - k):idx[-1] + k]


def speak(parts: list[tuple[str, str]], pauses: list[float], persona: str, secs: float, lead: float, seed: int,
          device: str = "mlx") -> tuple[np.ndarray, int, dict]:
    clips, sr = [], 24000
    for k, (text, delivery) in enumerate(parts):
        w, sr = say(text, f"{persona}. {delivery}".strip(), seed + k)
        clips.append(trim(w, sr))
    out, t, rows = [np.zeros(int(lead * sr), np.float32)], lead, []
    for i, c in enumerate(clips):
        rows.append({"text": parts[i][0], "delivery": parts[i][1], "start": round(t, 3), "end": round(t + len(c) / sr, 3)})
        out.append(c); t += len(c) / sr
        if i < len(clips) - 1:
            p = pauses[i] if i < len(pauses) else 0.6
            out.append(np.zeros(int(p * sr), np.float32)); t += p
    w = np.concatenate(out)
    n = int(round(secs * sr))
    fits = len(w) <= n - int(0.3 * sr)          # at least 0.3 s of tail room
    w = np.pad(w, (0, max(0, n - len(w))))[:n]
    w = w / (np.max(np.abs(w)) + 1e-9) * 0.7    # peak -3 dBFS; the clip's loudnorm sets the final level
    return w, sr, {"parts": rows, "speech_end": rows[-1]["end"] if rows else 0, "fits": fits, "secs": secs}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", required=True); ap.add_argument("--persona", required=True)
    ap.add_argument("--secs", type=float, default=8.04); ap.add_argument("--lead", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--device", default="mlx")
    ap.add_argument("--part", nargs=2, action="append", metavar=("TEXT", "DELIVERY"), required=True)
    ap.add_argument("--pause", type=float, action="append", default=[])
    a = ap.parse_args()
    w, sr, info = speak([tuple(p) for p in a.part], a.pause, a.persona, a.secs, a.lead, a.seed, a.device)
    sf.write(a.o, w, sr)
    info["file"] = a.o
    print(json.dumps(info))
