#!/usr/bin/env python3
"""delivery.py — is a line acted or recited? The delivery meter (2026-09-27, iteration 5; `docs/dialogue-sync.md`).
Local, CPU. No human rater: every number here is calibrated on known answers (RAVDESS: the same sentences by the same
actors, neutral vs strong emotion; see rig/sync/CALIBRATION.md) before it is trusted on our shots.

  voice (the separated vocal track, Demucs)
    pitch_sd_st    pitch standard deviation in semitones over voiced frames (Praat via parselmouth). Monotone = low.
    pitch_range_st 10th-90th percentile pitch range in semitones
    loud_sd_db     loudness standard deviation over voiced frames (dB)
    rate_wps       words per second of speech (forced-aligned words over the aligned speech span), when a line is given
    pauses         silences of 250 ms or more inside the speech span
    arousal, valence, dominance   audeering wav2vec2-large-robust-12-ft-emotion-msp-dim (0..1; CC BY-NC-SA 4.0,
                   local research use)
  face (the largest tracked face; MediaPipe blendshapes on S3FD crops)
    face_motion    mean per-frame change of the brow, eye and cheek blendshapes (speech-driven jaw and lips excluded)
    brow_sd        standard deviation of browInnerUp + browDown (does the brow act at all)
    smile_speaking mean mouthSmile while the voice is on (grin while talking: a lip-sync risk)

  delivery.py <clip.mp4> [--line "..."]      one JSON line per clip
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import syncmeter as sm  # noqa: E402  (re-execs into the sync venv)
import numpy as np  # noqa: E402

SER_ID = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
_ser = None


def ser(voice16: np.ndarray) -> dict:
    """Arousal, dominance, valence (0..1) of the voice."""
    global _ser
    import torch
    import torch.nn as nn
    from transformers import Wav2Vec2Processor
    from transformers.models.wav2vec2.modeling_wav2vec2 import Wav2Vec2Model, Wav2Vec2PreTrainedModel

    class Head(nn.Module):
        def __init__(self, c):
            super().__init__(); self.dense = nn.Linear(c.hidden_size, c.hidden_size)
            self.dropout = nn.Dropout(c.final_dropout); self.out_proj = nn.Linear(c.hidden_size, c.num_labels)
        def forward(self, x): return self.out_proj(self.dropout(torch.tanh(self.dense(self.dropout(x)))))

    class EmotionModel(Wav2Vec2PreTrainedModel):
        def __init__(self, c):
            super().__init__(c); self.config = c; self.wav2vec2 = Wav2Vec2Model(c); self.classifier = Head(c); self.post_init()
        def forward(self, x):
            h = self.wav2vec2(x)[0].mean(dim=1)
            return self.classifier(h)

    if _ser is None:
        _ser = (Wav2Vec2Processor.from_pretrained(SER_ID), EmotionModel.from_pretrained(SER_ID).eval())
    proc, model = _ser
    x = proc(voice16, sampling_rate=16000)["input_values"][0]
    with torch.no_grad():
        a, d, v = model(torch.from_numpy(np.asarray(x, np.float32))[None])[0].tolist()
    return {"arousal": round(a, 3), "dominance": round(d, 3), "valence": round(v, 3)}


def prosody(voice16: np.ndarray, span: tuple[float, float] | None) -> dict:
    import parselmouth
    snd = parselmouth.Sound(voice16.astype(np.float64), sampling_frequency=16000)
    if span:
        snd = snd.extract_part(from_time=max(0, span[0] - 0.05), to_time=span[1] + 0.05)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=70, pitch_ceiling=600)
    f0 = pitch.selected_array["frequency"]; f0 = f0[f0 > 0]
    res = {}
    if len(f0) >= 10:
        st = 12 * np.log2(f0 / np.median(f0))
        res["pitch_sd_st"] = round(float(np.std(st)), 2)
        res["pitch_range_st"] = round(float(np.percentile(st, 90) - np.percentile(st, 10)), 2)
        res["pitch_median_hz"] = round(float(np.median(f0)), 1)
    inten = snd.to_intensity(time_step=0.01).values[0]
    voiced = inten[inten > inten.max() - 25]
    if len(voiced) > 10: res["loud_sd_db"] = round(float(np.std(voiced)), 2)
    return res


def pauses(voice16: np.ndarray, span: tuple[float, float]) -> int:
    hop = 160
    e = np.array([np.sqrt(np.mean(voice16[i:i + hop] ** 2)) for i in range(0, len(voice16) - hop, hop)])
    db = 20 * np.log10(e + 1e-6); on = db > db.max() - 30
    a, b = int(span[0] * 100), int(span[1] * 100)
    run, n = 0, 0
    for x in on[a:b]:
        if not x: run += 1
        else:
            if run >= 25: n += 1
            run = 0
    return n


def face(frames, fps, voiced) -> dict:
    per = sm.faces_per_frame(frames, fps)
    tracks = sm.track_faces(per)
    if not tracks: return {}
    tr = max(tracks, key=lambda t: len(t) * np.median([f["hshare"] for f in t.values()]))
    idx = sorted(i for i in tr if tr[i].get("blend"))
    if len(idx) < 6: return {}
    keys = ["browInnerUp", "browDownLeft", "browDownRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft",
            "eyeWideRight", "cheekPuff"]
    M = np.array([[tr[i]["blend"].get(k, 0.0) for k in keys] for i in idx])
    brow = M[:, 0] + (M[:, 1] + M[:, 2]) / 2
    smile = np.array([(tr[i]["blend"].get("mouthSmileLeft", 0) + tr[i]["blend"].get("mouthSmileRight", 0)) / 2 for i in idx])
    sp = np.array([voiced[i] if i < len(voiced) else False for i in idx])
    return {"face_motion": round(float(np.mean(np.abs(np.diff(M, axis=0)).sum(1))), 4),
            "brow_sd": round(float(np.std(brow)), 4),
            "smile_speaking": round(float(smile[sp].mean()), 3) if sp.any() else None}


def measure(clip: Path, line: str | None = None) -> dict:
    p = sm.probe(clip); fps = p["fps"]
    voice = sm.vocals16k(clip)
    frames = sm.read_frames(clip, p["w"], p["h"])
    env = sm.envelope(voice, len(frames), fps)
    db = 20 * np.log10(env + 1e-6); voiced = db > max(db.max() - 30, -50)
    res: dict = {"clip": str(clip)}
    span = None
    if line:
        al = sm.align(voice, line)
        if al:
            span = (al[0]["start"], al[-1]["end"])
            res["rate_wps"] = round(len(al) / max(0.3, span[1] - span[0]), 2)
            res["pauses"] = pauses(voice, span)
            res["speech_span"] = [round(span[0], 2), round(span[1], 2)]
    if span is None and voiced.any():
        vi = np.where(voiced)[0]; span = (vi[0] / fps, (vi[-1] + 1) / fps)
    res.update(prosody(voice, span))
    if span:
        a, b = int(span[0] * 16000), int(span[1] * 16000)
        res.update(ser(voice[a:b] if b - a > 8000 else voice))
    res.update(face(frames, fps, voiced))
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("clips", nargs="+"); ap.add_argument("--line")
    a = ap.parse_args()
    for c in a.clips:
        try: r = measure(Path(c).expanduser(), a.line)
        except Exception as e: r = {"clip": c, "error": repr(e)}
        print(json.dumps(r), flush=True)
