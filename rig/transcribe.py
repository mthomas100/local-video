#!/usr/bin/env python3
"""transcribe.py <clip.mp4>... — what each clip's audio says, as JSON {path: text} (2026-09-24).

Runs under mlx-audio's venv (~/repos/mlx-audio/.venv/bin/python; rig/precheck.py --transcribe calls
it) with Parakeet TDT 0.6B v3, the model the pi `dictate` skill uses: English plus 24 European
languages, auto-detected, about 2.6 GB of GPU memory. Why: nothing checked a film's audio before, and
nobody had verified that non-English dialogue comes out as that language (the
2026-09-24 post-mortem). It uses the GPU, so the film-rig tools call it
only while the language model is unloaded, right after a render.
"""
import json
import os
import subprocess
import sys
import tempfile

MODEL = os.environ.get("RIG_STT_MODEL", "mlx-community/parakeet-tdt-0.6b-v3")
os.environ.setdefault("HF_HUB_OFFLINE", "1")   # the rig runs with the internet off; the model is in the HF cache


def main(paths: list[str]) -> int:
    from mlx_audio.stt.utils import load_model
    import mlx.core as mx

    model = load_model(MODEL)
    out = {}
    with tempfile.TemporaryDirectory() as td:
        for p in paths:
            wav = os.path.join(td, "a.wav")
            r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", p, "-vn",
                                "-ac", "1", "-ar", "16000", wav])
            if r.returncode or not os.path.exists(wav):
                out[p] = "(no audio track)"
                continue
            res = model.generate(wav)
            text = res if isinstance(res, str) else getattr(res, "text", "")
            out[p] = " ".join(str(text or "").split()) or "(no speech)"
            mx.clear_cache()
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
