#!/usr/bin/env python3
"""syncmeter.py — the dialogue-sync meter that replaces rig/audit/lipsync.py (2026-09-27, iteration 5). Local, CPU.

Why: the old meter correlated the largest face's lip opening with the loudness of the whole mix, and its pass rule
called a planted 400 ms offset "in sync" (`docs/dialogue-sync.md`). This meter uses independent local
instruments and returns UNMEASURABLE, never a pass, when it cannot see the speaker:

  voice     Demucs htdemucs separates the speech from ambience and effects (the old meter heard the hum and water)
  faces     MediaPipe Face Landmarker, every face in every frame (478 points + blendshapes), tracked across frames
  syncnet   SyncNet v2 (Chung & Zisserman; joonson/syncnet_python weights) on each face track's crop against the voice:
            the AV offset (the lag of minimum embedding distance, +-15 frames) and confidence (median - min distance).
            SyncNet is trained at 25 fps; our 24 fps clips are measured by re-timing the AUDIO by 24/25 (sample count
            only, so relative sync is untouched) and converting the frame offset back at 1000/24 ms per frame.
  speaker   the face track with the highest SyncNet confidence speaks (active-speaker detection by AV agreement);
            coverage = share of the voiced frames in which that face is visible and at least min_face_px tall
            (v3: 32 px, measured on planted shrunk mouths; v2 used 10% of the frame height, never tested below 12%)
  faces     (v3) S3FD at 0.5 scale, at 1.0 when the largest face is under 96 px (v2: 0.25, blind under ~64 px)
  others    (v3) a second face that follows the voice at the speaker's offset while both are on screen: FAIL (M9)
  envelope  the speaker's inner-lip opening against the voice envelope: correlation and best lag (a second opinion)
  windows   SyncNet offset in the first and last third of the speech (drift inside a clip, root cause M2)
  words     forced alignment of the asked line on the separated voice (torchaudio MMS_FA): word times, the speech
            onset (root cause M4: speech inside the first conditioned latent), and at every p/b/m the lip closure
            (visemes: a mouth that moves without forming the words fails here, root cause M3)

  syncmeter.py <clip.mp4> [--line "the asked words"] [--json out.json] [--overlay dir]   one JSON line per clip
  syncmeter.py --verdict <clip.mp4> ...        also print the one-line gate verdict (§4.4)

Sign convention of offset_ms (the handoff's): POSITIVE = AUDIO EARLY (the voice comes before the mouth), negative =
audio late. rig/sync/make_controls.py plants the opposite sign (planted +200 = audio delayed = offset -200 here).
Thresholds live in THRESH and are set by the calibration in rig/sync/CALIBRATION.md; METER_VERSION changes with them.
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path

VENV = Path.home() / ".cache/local-video/sync-venv/bin/python"
try:
    import numpy as np, torch, cv2  # noqa: F401
    import mediapipe as mp  # noqa: F401
except ImportError:
    if os.environ.get("SYNCMETER_REEXEC") != "1" and VENV.exists():
        os.environ["SYNCMETER_REEXEC"] = "1"; os.execv(str(VENV), [str(VENV), os.path.abspath(sys.argv[0]), *sys.argv[1:]])  # the calling script, when imported
    raise

CACHE = Path.home() / ".cache/local-video"
SYNCNET_SRC = CACHE / "syncnet/src"
SYNCNET_W = CACHE / "syncnet/syncnet_v2.model"
FACE_TASK = CACHE / "face_landmarker.task"
METER_VERSION = "v3"
THRESH = {
    "min_face_px": 32,         # speaker face height in pixels below which the meter cannot see the mouth (meter v3,
                               # 2026-10-03: planted offsets recovered within 7 ms down to 26-px faces; CALIBRATION §9.
                               # Until v2 this was 10% of the frame height, never tested below 12%)
    "min_coverage": 0.50,      # share of voiced frames with the speaker's face visible (liminal shot 2, a medium shot
                               # with its face in 59% of the speech, measured at conf 9.2, same offset as its raw clip)
    "min_conf": 4.2,           # SyncNet confidence below which the mouth does not follow this voice. Calibrated
                               # 2026-09-27 (rig/sync/CALIBRATION.md): frozen mouths and different-words swaps 0.8-3.74
                               # (clown and RAVDESS footage); real in-sync speech 4.66 (RAVDESS sad, strong) to 10.0
    "min_words": 0.60,         # share of the asked words the forced aligner finds (a swapped voice: 3/11)
    "edge_frames": 14,         # a best offset at the +-15 frame search edge = no sync peak (frozen and swapped controls)
    "early_ms": 45,            # audio-early limit (ITU-R BT.1359 detectability, about 45 ms)
    "late_ms": 125,            # audio-late limit (BT.1359 detectability, about 125 ms)
}
torch.set_num_threads(max(1, (os.cpu_count() or 8) // 2))


# ---------- media ----------
def probe(clip: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                          "stream=r_frame_rate,width,height,nb_read_packets", "-of", "json", str(clip)],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return {"fps": float(a) / float(b), "w": int(s["width"]), "h": int(s["height"]), "n": int(s["nb_read_packets"])}


def read_frames(clip: Path, w: int, h: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def read_audio(clip: Path, sr: int, ch: int = 1) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vn", "-ac", str(ch), "-ar", str(sr), "-f",
                          "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32)
    return a.reshape(-1, ch).T if ch > 1 else a


_demucs = None
def vocals16k(clip: Path) -> np.ndarray:
    """The separated voice at 16 kHz mono (htdemucs, CPU)."""
    global _demucs
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    import torchaudio.functional as AF
    if _demucs is None:
        _demucs = get_model("htdemucs"); _demucs.eval()
    x = torch.from_numpy(read_audio(clip, 44100, 2).copy())
    if x.shape[-1] == 0:
        return np.zeros(0, np.float32)
    ref = x.mean(0); m, s = ref.mean(), ref.std() + 1e-8
    with torch.no_grad():
        out = apply_model(_demucs, ((x - m) / s)[None], device="cpu", progress=False, split=True, overlap=0.25)[0]
    v = out[_demucs.sources.index("vocals")] * s + m
    return AF.resample(v.mean(0), 44100, 16000).numpy().astype(np.float32)


# ---------- faces ----------
_s3fd = None
_landmarker = None
def detect_scale(frames: np.ndarray) -> float:
    """The scale S3FD runs at (meter v3, 2026-10-03). S3FD's smallest anchor is 16 px, so at scale s it misses faces
    under about 16/s px: the old fixed 0.25 on 1280-px frames saw no face under ~64 px, and the shot lab's shrink test
    found every miss at 2.5-3.5% face height was the detector, not SyncNet (rig/sync/CALIBRATION.md §9). Probe six frames
    at 0.5; use 1.0 when none shows a face or the largest face is under 96 px (a small speaker). Keying on the largest
    face keeps a small background face from tripling the cost of a close-up (Rosa, clown-sighting 12: 180 s at 1.0)."""
    global _s3fd
    idx = np.linspace(0, len(frames) - 1, 6).astype(int)
    hs = [b[3] - b[1] for i in idx for b in _s3fd.detect_faces(frames[i], conf_th=0.9, scales=[0.5])[:4]]
    global _last_scale
    _last_scale = 0.5 if hs and max(hs) >= 96 else 1.0
    return _last_scale


_last_scale = None


def faces_per_frame(frames: np.ndarray, fps: float, stride: int = 2) -> list[list[dict]]:
    """Every face per frame: box (x0,y0,x1,y1 px), height share, inner-lip opening / face height, blendshapes.
    Detection: S3FD (the detector of SyncNet's own pipeline) on every `stride`-th frame. MediaPipe's and macOS Vision's
    detectors missed painted clown faces (liminal-clowns shot 7, a frontal close-up: 13% and 31% of frames; S3FD 100%,
    2026-09-27). Lips: MediaPipe Face Landmarker on each face crop (IMAGE mode, the crop upscaled)."""
    global _s3fd, _landmarker
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    if _s3fd is None:
        cwd = os.getcwd(); os.chdir(SYNCNET_SRC)          # S3FD loads its weights by a relative path
        try:
            sys.path.insert(0, str(SYNCNET_SRC)); from detectors import S3FD; _s3fd = S3FD(device="cpu")
        finally: os.chdir(cwd)
    if _landmarker is None:
        opts = vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=str(FACE_TASK),
                                            delegate=mpt.BaseOptions.Delegate.CPU), running_mode=vision.RunningMode.IMAGE,
                                            num_faces=1, output_face_blendshapes=True, min_face_detection_confidence=0.3,
                                            min_face_presence_confidence=0.3)
        _landmarker = vision.FaceLandmarker.create_from_options(opts)
    H, W = frames.shape[1:3]
    scale = detect_scale(frames)
    res: list[list[dict]] = [[] for _ in range(len(frames))]
    for i in range(0, len(frames), stride):
        f = frames[i]
        boxes = _s3fd.detect_faces(f, conf_th=0.9, scales=[scale])
        fl = []
        for b in boxes[:4]:
            x0, y0, x1, y1 = map(float, b[:4])
            fh = max(1.0, y1 - y0)
            d = {"box": (x0, y0, x1, y1), "hshare": fh / H, "open": None, "jaw": None, "close": None, "mouth": None}
            # lips on a crop around the box, upscaled to 384 px wide
            pad = 0.35 * fh
            cx0, cy0, cx1, cy1 = int(max(0, x0 - pad)), int(max(0, y0 - pad)), int(min(W, x1 + pad)), int(min(H, y1 + pad))
            crop = f[cy0:cy1, cx0:cx1]
            if crop.size:
                k = 384 / crop.shape[1]
                cr = cv2.resize(crop, (384, max(1, int(crop.shape[0] * k))))
                r = _landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(cr)))
                if r.face_landmarks:
                    pts = r.face_landmarks[0]
                    xy = np.array([[cx0 + p.x * cr.shape[1] / k, cy0 + p.y * cr.shape[0] / k] for p in pts])
                    lh = max(1.0, xy[:, 1].max() - xy[:, 1].min())
                    bs = {c.category_name: c.score for c in r.face_blendshapes[0]} if r.face_blendshapes else {}
                    d.update({"open": float(np.linalg.norm(xy[13] - xy[14]) / lh), "jaw": bs.get("jawOpen"),
                              "close": bs.get("mouthClose"), "mouth": xy[[61, 291, 13, 14, 0, 17]].tolist(),
                              "blend": {k2: round(v, 3) for k2, v in bs.items() if k2 in BLEND_KEEP}})
            fl.append(d)
        res[i] = fl
    return res


BLEND_KEEP = {"jawOpen", "mouthClose", "browInnerUp", "browDownLeft", "browDownRight", "eyeSquintLeft", "eyeSquintRight",
              "eyeWideLeft", "eyeWideRight", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
              "mouthPucker", "mouthFunnel", "cheekPuff", "eyeBlinkLeft", "eyeBlinkRight"}


def track_faces(per: list[list[dict]]) -> list[dict[int, dict]]:
    """Greedy tracks: a face joins the track whose last box centre is nearest (within half a face)."""
    tracks: list[dict[int, dict]] = []
    for i, fl in enumerate(per):
        used = set()
        for f in sorted(fl, key=lambda f: -f["hshare"]):
            cx, cy = (f["box"][0] + f["box"][2]) / 2, (f["box"][1] + f["box"][3]) / 2
            size = f["box"][3] - f["box"][1]
            best, bd = None, 1e9
            for t, tr in enumerate(tracks):
                if t in used: continue
                last = max(tr); g = tr[last]
                if i - last > 12: continue
                d = np.hypot(cx - (g["box"][0] + g["box"][2]) / 2, cy - (g["box"][1] + g["box"][3]) / 2)
                if d < 0.5 * max(size, g["box"][3] - g["box"][1]) and d < bd: best, bd = t, d
            if best is None:
                tracks.append({i: f}); used.add(len(tracks) - 1)
            else:
                tracks[best][i] = f; used.add(best)
    return [t for t in tracks if len(t) >= 6]


# ---------- SyncNet ----------
_syncnet = None
def syncnet():
    global _syncnet
    if _syncnet is None:
        sys.path.insert(0, str(SYNCNET_SRC))
        from SyncNetModel import S
        net = S(num_layers_in_fc_layers=1024)
        state = torch.load(str(SYNCNET_W), map_location="cpu")
        net.load_state_dict(state.state_dict() if hasattr(state, "state_dict") else state)
        _syncnet = net.eval()
    return _syncnet


def crops(frames: np.ndarray, track: dict[int, dict], n: int) -> np.ndarray:
    """224x224 BGR crops the way syncnet_python's run_pipeline.crop_video makes them (crop_scale 0.4), with the
    box median-smoothed and held across gaps."""
    idx = np.array(sorted(track))
    boxes = np.array([track[i]["box"] for i in idx])
    allb = np.stack([np.interp(np.arange(n), idx, boxes[:, k]) for k in range(4)], 1)
    from scipy.signal import medfilt
    allb = np.stack([medfilt(allb[:, k], 5) for k in range(4)], 1)
    out = np.zeros((n, 224, 224, 3), np.uint8)
    cs = 0.4
    for i in range(n):
        x0, y0, x1, y1 = allb[i]
        bs = max(x1 - x0, y1 - y0) / 2
        my, mx = (y0 + y1) / 2, (x0 + x1) / 2
        bsi = int(bs * (1 + 2 * cs))
        fr = cv2.copyMakeBorder(cv2.cvtColor(frames[i], cv2.COLOR_RGB2BGR), bsi, bsi, bsi, bsi,
                                cv2.BORDER_CONSTANT, value=(110, 110, 110))
        my, mx = my + bsi, mx + bsi
        face = fr[int(my - bs):int(my + bs * (1 + 2 * cs)), int(mx - bs * (1 + cs)):int(mx + bs * (1 + cs))]
        if face.size: out[i] = cv2.resize(face, (224, 224))
    return out


def syncnet_dists(crop: np.ndarray, voice16: np.ndarray, fps: float, vshift: int = 15) -> np.ndarray:
    """dists[frame, shift] (shift index k = offset vshift-k frames), SyncNet v2 on 5-frame windows."""
    import python_speech_features
    from scipy.signal import resample_poly
    # re-time: fps video frames are called 25 fps; the audio keeps its length in video frames
    a = resample_poly(voice16, int(round(fps * 1000)), 25000) if abs(fps - 25) > 0.01 else voice16
    mfcc = np.stack([np.array(i) for i in zip(*python_speech_features.mfcc((a * 32767).astype(np.int16), 16000))])
    cct = torch.from_numpy(mfcc[None, None].astype(np.float32))
    imtv = torch.from_numpy(np.transpose(crop[None], (0, 4, 1, 2, 3)).astype(np.float32))
    n = min(len(crop), mfcc.shape[1] // 4)
    last = n - 5
    net = syncnet()
    fi, fa = [], []
    with torch.no_grad():
        for i in range(0, last, 50):
            r = range(i, min(last, i + 50))
            fi.append(net.forward_lip(torch.cat([imtv[:, :, v:v + 5] for v in r], 0)))
            fa.append(net.forward_aud(torch.cat([cct[:, :, :, v * 4:v * 4 + 20] for v in r], 0)))
    fi, fa = torch.cat(fi), torch.cat(fa)
    fap = torch.nn.functional.pad(fa, (0, 0, vshift, vshift))
    w = 2 * vshift + 1
    d = torch.stack([torch.nn.functional.pairwise_distance(fi[[i]].repeat(w, 1), fap[i:i + w]) for i in range(len(fi))])
    return d.numpy()


def offset_conf(d: np.ndarray, rows: np.ndarray | None = None, vshift: int = 15) -> tuple[float, float, float]:
    """SyncNet's rule on the chosen rows: (offset frames, confidence, min dist). offset > 0 in SyncNet's convention."""
    dd = d if rows is None else d[rows]
    if len(dd) == 0: return 0, 0.0, 0.0
    m = dd.mean(0)
    k = int(np.argmin(m))
    frac = 0.0
    if 0 < k < len(m) - 1:   # parabolic vertex through the minimum and its neighbours: sub-frame offset
        a, b, c = m[k - 1], m[k], m[k + 1]
        den = a - 2 * b + c
        if den > 1e-9: frac = float(np.clip(0.5 * (a - c) / den, -0.5, 0.5))
    return vshift - (k + frac), float(np.median(m) - m[k]), float(m[k])


# ---------- words ----------
_fa = None
def align(voice16: np.ndarray, line: str) -> list[dict]:
    """Forced alignment of the asked words: [{word, start, end, score, chars:[(ch, t)]}] in seconds (MMS_FA, CPU)."""
    global _fa
    import re, torchaudio
    from torchaudio.pipelines import MMS_FA as B
    words = [w for w in re.sub(r"[^a-z' ]", " ", line.lower().replace("’", "'")).split() if re.sub("[^a-z]", "", w)]
    words = [re.sub("[^a-z]", "", w) for w in words]
    if not words or len(voice16) < 1600: return []
    if _fa is None: _fa = (B.get_model(with_star=False).eval(), B.get_tokenizer(), B.get_aligner())
    model, tok, aligner = _fa
    with torch.no_grad():
        em, _ = model(torch.from_numpy(voice16.copy())[None])
    spans = aligner(em[0], tok(words))
    ratio = len(voice16) / 16000 / em.shape[1]
    out = []
    for w, sp in zip(words, spans):
        out.append({"word": w, "start": round(sp[0].start * ratio, 3), "end": round(sp[-1].end * ratio, 3),
                    "score": round(float(np.mean([s.score for s in sp])), 3),
                    "chars": [(w[j], round((s.start + s.end) / 2 * ratio, 3)) for j, s in enumerate(sp)]})
    return out


# ---------- the meter ----------
def envelope(voice16: np.ndarray, n: int, fps: float) -> np.ndarray:
    hop = 16000 / fps
    return np.array([np.sqrt(np.mean(voice16[int(i * hop):int((i + 1) * hop)] ** 2)) if int(i * hop) < len(voice16)
                     else 0.0 for i in range(n)])


def measure(clip: Path, line: str | None = None, overlay: Path | None = None, one_line: bool = True,
            lines: list[str] | None = None, speakers: list | None = None) -> dict:
    t0 = time.time()
    p = probe(clip); fps = p["fps"]
    frames = read_frames(clip, p["w"], p["h"]); n = len(frames)
    voice = vocals16k(clip)
    env = envelope(voice, n, fps)
    db = 20 * np.log10(env + 1e-6)
    voiced = db > max(db.max() - 30, -50)
    res: dict = {"clip": str(clip), "meter": METER_VERSION, "fps": round(fps, 3), "frames": n,
                 "voiced_share": round(float(voiced.mean()), 2)}
    if voiced.sum() < 0.5 * fps:
        return {**res, "verdict": "NO-SPEECH", "why": "no voice in the separated vocal track",
                "secs": round(time.time() - t0, 1)}
    per = faces_per_frame(frames, fps)
    tracks = track_faces(per)
    res["faces_max"] = max((len(f) for f in per), default=0)
    ms_per = 1000 / fps
    cands = []
    for t, tr in enumerate(tracks):
        d = syncnet_dists(crops(frames, tr, n), voice, fps)
        rows = np.arange(len(d))
        vo = voiced[:len(d)] | np.roll(voiced[:len(d)], 2) | np.roll(voiced[:len(d)], -2)
        off, conf, mind = offset_conf(d, rows[vo[:len(d)]] if vo[:len(d)].sum() >= 10 else None)
        det = np.array(sorted(tr))
        near = np.array([det[np.argmin(np.abs(det - i))] for i in range(n)])
        vis = np.array([abs(near[i] - i) <= 3 and tr[near[i]]["hshare"] * p["h"] >= THRESH["min_face_px"] for i in range(n)])
        cov = float(vis[voiced].mean())
        cands.append({"track": t, "offset": off, "conf": conf, "mind": mind, "coverage": cov, "d": d, "tr": tr,
                      "hshare": float(np.median([f["hshare"] for f in tr.values()])),
                      "face_px": round(float(np.median([f["hshare"] for f in tr.values()])) * p["h"]), "vis": vis})
    res["tracks"] = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items() if k not in ("d", "tr", "vis")}
                     for c in cands]
    res["detect_scale"] = _last_scale
    if not cands:
        return {**res, "verdict": "UNMEASURABLE", "why": "no face found", "secs": round(time.time() - t0, 1)}
    sp = max(cands, key=lambda c: c["conf"] * (0.3 + min(1.0, c["coverage"])))
    # SyncNet offset > 0 = the voice comes before the mouth (audio early); checked on planted controls 2026-09-27
    # (planted +200 ms audio delay reads about -200 here).
    off_ms = sp["offset"] * ms_per
    res.update({"speaker_track": sp["track"], "offset_ms": round(off_ms), "conf": round(sp["conf"], 2),
                "coverage": round(sp["coverage"], 2), "face_h": round(sp["hshare"], 2), "face_px": sp["face_px"]})
    # another face that mouths the same line (meter v3, 2026-10-03; only when the shot has ONE quoted line: a scene
    # written as an exchange, A's line then B's, has two mouths that follow the voice by design, e.g. the
    # snow-maiden-ski-lift exchange): LTX's audio-video attention carries time, not
    # place (the LTX-2 report), and human raters found the right speaker in 24% of LTX-2.3's multi-speaker clips
    # (MTAVG-Bench), with "multi-lip single voice" a named failure. A second track counts when it is on screen at the
    # same time as the speaker for at least 30% of the voice and follows it at the speaker's offset (+-2 frames).
    others = []
    for c in (cands if one_line else []):
        if c is sp: continue
        both = (c["vis"] & sp["vis"])[voiced].mean() if voiced.any() else 0.0
        if c["conf"] >= THRESH["min_conf"] and abs(c["offset"] - sp["offset"]) <= 2 and abs(c["offset"]) < THRESH["edge_frames"] and both >= 0.3:
            others.append({"track": c["track"], "conf": round(c["conf"], 2), "offset_ms": round(c["offset"] * ms_per),
                           "face_px": c["face_px"], "together": round(float(both), 2)})
    res["other_mouths"] = others
    # a shot written as an exchange (meter v3, 2026-10-03, shot lab): one face cannot explain two people's voices, so
    # each line is measured on its own span and gets its own speaker (lab P2: the whole-clip read was conf 3.6, while
    # per line Dana's words followed the left face at conf 7.9 and Leo's the right face at 7.6-8.0, on both seeds)
    if lines and len(lines) >= 2:
        words = align(voice, " ".join(lines))
        counts = [len(l.split()) for l in lines]
        per_line, k = [], 0
        if words and len(words) >= 0.6 * sum(counts):
            for li, (ln, c) in enumerate(zip(lines, counts)):
                ws = words[k:k + c]; k += c
                if not ws: continue
                rows = np.arange(max(0, int(ws[0]["start"] * fps) - 2), min(n - 5, int(ws[-1]["end"] * fps) + 3))
                best = None
                for c2 in cands:
                    rr = rows[rows < len(c2["d"])]
                    if len(rr) < 6: continue
                    o2, cf2, _ = offset_conf(c2["d"], rr)
                    if abs(o2) >= THRESH["edge_frames"]: continue
                    if best is None or cf2 > best["conf"]:
                        best = {"track": c2["track"], "conf": round(cf2, 2), "offset_ms": round(o2 * ms_per),
                                "coverage": round(float(c2["vis"][rr].mean()), 2), "face_px": c2["face_px"]}
                per_line.append({"line": ln, "speaker": (speakers or [None] * len(lines))[li],
                                 "start_s": round(ws[0]["start"], 2), "end_s": round(ws[-1]["end"], 2), "face": best})
        res["lines"] = per_line
    # drift: offset in the first and last third of the voiced span
    vi = np.where(voiced[:len(sp["d"])])[0]
    if len(vi) >= 30:
        a, b = vi[:len(vi) // 3], vi[-(len(vi) // 3):]
        oa, ca, _ = offset_conf(sp["d"], a); ob, cb, _ = offset_conf(sp["d"], b)
        res["drift"] = {"first_ms": round(oa * ms_per), "first_conf": round(ca, 2),
                        "last_ms": round(ob * ms_per), "last_conf": round(cb, 2)}
    # envelope: the speaker's lip opening vs the voice
    tr = sp["tr"]; idx = np.array(sorted(i for i in tr if tr[i]["open"] is not None))
    res["lips_share"] = round(len(idx) / max(1, len(tr)), 2)
    if len(idx) < 6:
        res["secs"] = round(time.time() - t0, 1); res.update(verdict(res)); return res
    mo = np.interp(np.arange(n), idx, [tr[i]["open"] for i in idx])
    lip = {int(i): tr[i]["open"] for i in idx}
    lv = np.log(env + 1e-4)
    best, bl = -1.0, 0
    for lag in range(-int(0.5 * fps), int(0.5 * fps) + 1):
        x, y = (mo[lag:], lv[:n - lag]) if lag >= 0 else (mo[:n + lag], lv[-lag:])
        c = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else 0.0
        if lag == 0: res["env_corr0"] = round(c, 3)
        if c > best: best, bl = c, lag
    res["env_best"] = round(best, 3); res["env_offset_ms"] = round(bl * ms_per)   # lag>0: mouth follows voice
    # words and visemes
    if line:
        al = align(voice, line)
        if al:
            res["onset_s"] = al[0]["start"]
            res["word_score"] = round(float(np.mean([w["score"] for w in al])), 3)
            res["words_weak"] = sum(w["score"] < 0.3 for w in al)
            res["words"] = len(al)
            spk = np.array([lip[i] for i in lip if voiced[i]]) if any(voiced[i] for i in lip) else mo
            ref_open = float(np.median(spk))
            closes, rnd = [], []
            for w in al:
                for ch, t in w["chars"]:
                    if ch in "pbm":
                        i = int(round(t * fps))
                        win = [j for j in range(i - 3, i + 4) if j in lip]
                        if win: closes.append(min(lip[j] for j in win) <= 0.5 * ref_open)
            rng = np.random.default_rng(0)
            vv = [i for i in np.where(voiced)[0] if i in lip]
            for i in rng.choice(vv, size=min(40, len(vv)), replace=False) if vv else []:
                win = [j for j in range(i - 3, i + 4) if j in lip]
                rnd.append(min(lip[j] for j in win) <= 0.5 * ref_open)
            if closes:
                res["bilabials"] = len(closes)
                res["bilabial_closed"] = round(float(np.mean(closes)), 2)
                res["random_closed"] = round(float(np.mean(rnd)), 2) if rnd else None
    if overlay:
        draw_overlay(frames, tr, voiced, overlay, clip.stem)
    res["secs"] = round(time.time() - t0, 1)
    res.update(verdict(res))
    return res


def verdict(r: dict) -> dict:
    T = THRESH
    if r.get("verdict") in ("NO-SPEECH", "UNMEASURABLE"): return {}
    if r.get("lines"):   # an exchange: every line measured on its own span (meter v3)
        if r.get("words") and (r["words"] - r.get("words_weak", 0)) / r["words"] < T["min_words"]:
            return {"verdict": "FAIL", "why": f"the voices do not say the asked lines ({r['words'] - r.get('words_weak', 0)}"
                    f"/{r['words']} words heard)", "cause": "W"}
        for i, L in enumerate(r["lines"], 1):
            f = L["face"]
            if not f: return {"verdict": "FAIL", "why": f"line {i}: no face follows its words", "cause": "M3"}
            if f["coverage"] < T["min_coverage"]:
                return {"verdict": "UNMEASURABLE", "why": f"line {i}: its speaker is visible in {f['coverage']:.0%} of it", "cause": "V1"}
            if f["conf"] < T["min_conf"]:
                return {"verdict": "FAIL", "why": f"line {i}: the mouth does not follow it (conf {f['conf']})", "cause": "M3"}
            if f["offset_ms"] > T["early_ms"] or f["offset_ms"] < -T["late_ms"]:
                return {"verdict": "FAIL", "why": f"line {i}: offset {f['offset_ms']:+d} ms", "cause": "M1"}
        named = [(L["speaker"], L["face"]["track"]) for L in r["lines"] if L["speaker"]]
        for (a1, t1) in named:
            for (a2, t2) in named:
                if a1 != a2 and t1 == t2:
                    return {"verdict": "FAIL", "why": f"one face speaks both {a1}'s and {a2}'s lines", "cause": "M10"}
        return {"verdict": "PASS", "why": f"in sync, {len(r['lines'])} lines each from its own speaker"}
    if r["coverage"] < T["min_coverage"]:
        return {"verdict": "UNMEASURABLE", "why": f"speaker face visible in {r['coverage']:.0%} of the speech",
                "cause": "V1"}
    off = r["offset_ms"]
    if r.get("words") and (r["words"] - r.get("words_weak", 0)) / r["words"] < T["min_words"]:
        return {"verdict": "FAIL", "why": f"the voice does not say the asked line ({r['words'] - r.get('words_weak', 0)}"
                f"/{r['words']} words heard)", "cause": "W"}
    if abs(off) >= T["edge_frames"] * 1000 / r.get("fps", 24):
        return {"verdict": "FAIL", "why": f"no sync peak (best offset at the search edge, conf {r['conf']})", "cause": "M3"}
    if r["conf"] < T["min_conf"]:
        return {"verdict": "FAIL", "why": f"mouth does not follow the voice (conf {r['conf']} < {T['min_conf']})",
                "cause": "M3"}
    if off > T["early_ms"] or off < -T["late_ms"]:
        return {"verdict": "FAIL", "why": f"offset {off:+d} ms ({'audio early' if off > 0 else 'audio late'})",
                "cause": "M1"}
    if r.get("other_mouths"):
        o = r["other_mouths"][0]
        return {"verdict": "FAIL", "why": f"another face mouths the line too (track {o['track']}, conf {o['conf']})", "cause": "M9"}
    return {"verdict": "PASS", "why": "in sync"}


def line_of(shot: str, r: dict) -> str:
    """The one-line gate verdict (`docs/dialogue-sync.md`)."""
    if r.get("verdict") == "NO-SPEECH": return f"sync {shot}: NO-SPEECH (no voice heard) → the line was not spoken; redo"
    parts = [f"sync {shot}: {r['verdict']}"]
    if r.get("lines"):   # an exchange: one entry per line (who, offset, conf)
        for i, L in enumerate(r["lines"], 1):
            f = L["face"] or {}
            parts.append(f"line {i}{' ' + L['speaker'] if L['speaker'] else ''}: "
                         + (f"{f['offset_ms']:+d} ms conf {f['conf']} (face {f['track']})" if f else "no face"))
    elif "offset_ms" in r:
        o = r["offset_ms"]; parts.append(f"offset {o:+d} ms ({'audio early' if o > 0 else 'audio late' if o < 0 else 'aligned'})")
        parts.append(f"conf {r['conf']}")
        parts.append(f"coverage {r['coverage']:.2f}")
    if "words" in r: parts.append(f"words {r['words'] - r['words_weak']}/{r['words']}")
    act = {"PASS": "keep", "FAIL": "retake",
           "UNMEASURABLE": "retake with the speaker's face in view through the line (32 px or more: any framing from close-up to full length)"}
    if r.get("cause") == "M9":
        act["FAIL"] = "retake with everyone else written silent, mouth closed, or give the other person their own shot"
    if r.get("cause") == "M10":
        act["FAIL"] = "retake (a new seed), or give each speaker's line its own shot"
    return ", ".join(parts) + f" [{r.get('why', '')}] → {act.get(r.get('verdict'), 'retake')}"


def draw_overlay(frames, tr, voiced, out: Path, stem: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    idx = sorted(i for i in tr if voiced[i] and tr[i]["mouth"]) or sorted(i for i in tr if tr[i]["mouth"]) or sorted(tr)
    pick = [idx[int(k * (len(idx) - 1) / 4)] for k in range(5)]
    tiles = []
    for i in pick:
        f = cv2.cvtColor(frames[i], cv2.COLOR_RGB2BGR).copy()
        x0, y0, x1, y1 = map(int, tr[i]["box"])
        cv2.rectangle(f, (x0, y0), (x1, y1), (0, 255, 0), 2)
        for (x, y) in (tr[i]["mouth"] or []): cv2.circle(f, (int(x), int(y)), 3, (0, 0, 255), -1)
        cv2.putText(f, f"{i} open {tr[i]['open'] or 0:.3f}", (x0, max(20, y0 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 255), 2)
        pad = int(0.3 * (y1 - y0))
        crop = f[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]
        tiles.append(cv2.resize(crop, (300, int(300 * crop.shape[0] / max(1, crop.shape[1])))))
    h = max(t.shape[0] for t in tiles)
    cv2.imwrite(str(out / f"{stem}-mouth.jpg"), np.hstack([cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0,
                                                                                cv2.BORDER_CONSTANT) for t in tiles]))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+"); ap.add_argument("--line"); ap.add_argument("--json")
    ap.add_argument("--overlay"); ap.add_argument("--verdict", action="store_true")
    a = ap.parse_args()
    rows = []
    for c in a.clips:
        try: r = measure(Path(c).expanduser(), a.line, Path(a.overlay) if a.overlay else None)
        except Exception as e: r = {"clip": c, "error": repr(e)}
        rows.append(r); print(json.dumps(r), flush=True)
        if a.verdict and "error" not in r: print(line_of(Path(c).stem, r), flush=True)
    if a.json: Path(a.json).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
