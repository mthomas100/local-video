#!/usr/bin/env python3
"""char-keyframe.py — the iteration-3 render experiments for identity and landmarks, in 9:16 portrait (2026-09-26).

the iteration-3 plan (not published). Every render goes through bin/vidgen (sidecar JSON per clip) one at a time,
into ~/Videos/vidgen/rig-tests/iter3-0926/<step>/. A clip whose .json sidecar exists is skipped, so a step can be
rerun to resume. Each GPU job first checks that nothing else holds the GPU (no LTX render, no image model, no ds4 or
llama server, llama-swap empty).

  e1      mode consistency: Marrow's lines 5, 13 and 16 of halloween-clowns-sf at the project seed, fast and quality;
          and line 13 at two more seeds in both modes (does a mode keep one look across lines, across seeds?)
  e2      a character plate: a 2 s well-lit medium shot of Marrow (LTX), its best face frame (bin/pick-face-frame),
          then line 16 conditioned on it with `--image plate IDX STRENGTH`, IDX 0 and 96, STRENGTH 0.2/0.3/0.4,
          against the same line unconditioned
  e2q     the same plate idea with an image-model portrait of Marrow as the plate (Qwen-Image-2.1)
  stills  landmark first frames with Qwen-Image-2.1: Coit Tower and the Painted Ladies, 3 seeds each
  k2      keyframe-first against text-only, quality mode: the same line and seed, with and without the still
  boards  identity boards of e1/e2 results (review-bench style) for eye checks and the director's answer

  char-keyframe.py <step> [--size 480p|720p] [--seconds 5] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parents[2]
VIDGEN = REPO / "bin/vidgen"
OUT = HOME / "Videos/vidgen/rig-tests/iter3-0926"
MFLUX_QWEN = HOME / "repos/imagegen/.venv/bin/mflux-generate-qwen-2.1"
SEED = 1031  # halloween-clowns-sf's project seed

# The last film's look (stories/projects/17-halloween-clowns-sf.txt): style only, appended after each line.
BIBLE = ("Magenta and cyan neon on black, one crimson accent, low key from neon signs and headlights, handheld and "
         "close, shallow depth of field with rain on glass, wet streets and spider webs, a clean rectangular full-frame "
         "image. Night rain, a distant siren, a saxophone.")
MARROW = ("Marrow, a man of about forty, white face paint with a cracked porcelain finish, a red nose, a tattered "
          "black-and-purple costume with silver bells")
LINES = {
    # halloween-clowns-sf lines 5, 13 and 16, verbatim (tokens removed)
    "m5": (f"On a neon-lit San Francisco street at night, {MARROW}, the only person in the shot, stands under a magenta "
           "neon sign, silver spider webs sagging overhead. A medium-wide shot holds as he raises one hand. Low key from "
           "the neon and headlights. Rain, a distant siren, he says, 'The streets are ours.'"),
    "m13": ("On a San Francisco street at night, a slow push-in on Marrow's face alone, a man of about forty, white face "
            "paint with a cracked porcelain finish, a red nose, a tattered black-and-purple costume with silver bells. He "
            "grins wide and leans toward the camera, rain running down the white paint. Low key, one magenta neon sign "
            "and a headlight. Rain, a low laugh, he says, 'The streets are ours.'"),
    "m16": (f"On a San Francisco street at night, a medium shot holds on {MARROW}, the only person in the shot, staring "
            "at the camera, a real giant pumpkin taller than him glowing behind him, silver spider webs sagging overhead. "
            "The camera slowly pushes in. Low key, one magenta neon sign. Rain, a distant siren, he says, 'Happy Halloween.'"),
    "plate": (f"On a San Francisco street at night, a medium shot of {MARROW}, the only person in the shot, standing still "
              "and facing the camera, his whole face and costume evenly lit by a soft white streetlamp in front of him, "
              "a magenta neon sign behind him. The camera holds still. Quiet rain."),
    # keyframe-first landmarks (the director prompt's physical descriptions; scale by people, never by objects)
    "coit": ("At Coit Tower on Telegraph Hill in San Francisco at night, a thick white fluted concrete tower with a ring "
             "of tall arched windows near its top, on the crest of a steep wooded hill above the bay, a slow aerial "
             "drone shot circles the tower. Silver spider webs drape from the top of the tower across the hilltop "
             "trees, and a real giant pumpkin taller than the people beside it glows orange on the plaza at its foot. "
             "Low key, the city lights and the bay below. Wind, rain, a distant siren."),
    "ladies": ("On Alamo Square in San Francisco at night, the Painted Ladies, a row of seven tall narrow wooden "
               "Victorian houses with steep pointed gables and bay windows, painted pastel blue, pink and yellow, "
               "stepping down a steep grassy hill with the lit downtown skyscrapers behind them, a slow aerial drone "
               "shot rises over the row. Silver spider webs drape between the gables, and a real giant pumpkin taller "
               "than the people beside it glows orange on the lawn. Low key, fog. Rain, a distant siren, a saxophone."),
}
# Keyframe-first for a character (step "mstills"): one still per shot from the same character sentence, each in
# that shot's own composition (lines 5, 13, 16), then animated with vidgen -i (step "mk2"). Tests whether identity
# holds across stills without one plate imposing its framing on every shot (e2/e2q: it does impose it).
MARROW_STILL = ("a real adult man of about forty who resembles no celebrity, Marrow: white clown face paint with a "
                "cracked porcelain finish, a red nose, short dark hair, a tattered black-and-purple costume with small "
                "silver bells")
MSHOTS = {
    "m5": ("Photorealistic night photograph, vertical 9:16 frame, medium-wide shot on a wet neon-lit San Francisco "
           f"street: {MARROW_STILL}, the only person in the frame, stands under a magenta neon sign raising one hand, "
           "silver spider webs sagging overhead. Low key, rain, a clean full-frame image, no text."),
    "m13": ("Photorealistic night photograph, vertical 9:16 frame, close-up of the face of " + MARROW_STILL +
            ", grinning wide and leaning toward the camera, rain running down the white paint, one magenta neon sign "
            "behind him. Low key, a clean full-frame image, no text."),
    "m16": ("Photorealistic night photograph, vertical 9:16 frame, medium shot on a San Francisco street at night: "
            f"{MARROW_STILL}, the only person in the frame, staring at the camera, a real giant carved Halloween pumpkin "
            "taller than him glowing orange behind him, silver spider webs sagging overhead. Low key, one magenta neon "
            "sign, rain, a clean full-frame image, no text."),
}
# First-frame prompts for the image model: the same place, as a still photograph in the film's look.
STILLS = {
    "coit": ("Photorealistic night photograph, vertical 9:16 frame, of Coit Tower on Telegraph Hill in San Francisco: a "
             "thick white fluted concrete tower with a ring of tall arched windows near its top, rising from the crest "
             "of a steep hill of dark cypress and eucalyptus trees, seen from a drone at the height of its windows. "
             "Silver spider webs drape from the top of the tower across the trees. A real giant carved Halloween "
             "pumpkin, taller than the two people standing beside it, glows orange on the plaza at the tower's foot. "
             "The lit city and the bay far below, rain and fog, magenta and cyan neon glow on black, one crimson "
             "accent. Low key, a clean full-frame image, no text."),
    "marrow": ("Photorealistic medium shot photograph, vertical 9:16 frame, of Marrow, a real adult man of about forty "
               "who resembles no celebrity: white clown face paint with a cracked porcelain finish, a red nose, short "
               "dark hair, a tattered black-and-purple costume with small silver bells, standing still and facing the "
               "camera on a wet San Francisco street at night, his face evenly lit by a soft white streetlamp, a "
               "magenta neon sign behind him. Low key, rain, a clean full-frame image, no text."),
    "ladies": ("Photorealistic night photograph, vertical 9:16 frame, of the Painted Ladies on Alamo Square in San "
               "Francisco: a row of seven tall narrow wooden Victorian houses with steep pointed gables and bay "
               "windows, painted pastel blue, pink and yellow, stepping down a steep grassy hill, the lit downtown "
               "skyscrapers behind them, seen from a drone above the park. Silver spider webs drape between the "
               "gables. A real giant carved Halloween pumpkin, taller than the two people standing beside it, glows "
               "orange on the lawn. Rain and fog, magenta and cyan neon glow on black, one crimson accent. Low key, a "
               "clean full-frame image, no text."),
}


def gpu_state(samples: int = 3) -> tuple[float, float]:
    """(mean GPU Device Utilization %, GB of system memory the GPU has in use), from ioreg (no sudo). Catches GPU
    jobs this script does not know by name: on 2026-09-26 a ComfyUI Trellis2 job held the GPU and a bench request
    waited 12 minutes inside ds4's vision encoder."""
    import re as _re, time as _time
    util, mem = [], 0.0
    for i in range(samples):
        out = subprocess.run(["ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"], capture_output=True, text=True).stdout
        m = _re.search(r'"Device Utilization %"=(\d+)', out)
        util.append(float(m.group(1)) if m else 0.0)
        m = _re.search(r'"In use system memory"=(\d+)', out)
        mem = max(mem, int(m.group(1)) / 1e9 if m else 0.0)
        if i + 1 < samples:
            _time.sleep(1)
    return sum(util) / len(util), mem


def other_gpu_jobs() -> str:
    """Known GPU users that are not ours (ComfyUI and 3D/image jobs of other sessions), by port and name."""
    if subprocess.run(["lsof", "-nP", "-iTCP:8189", "-sTCP:LISTEN"], capture_output=True).returncode == 0:
        return "a ComfyUI server listens on :8189"
    r = subprocess.run(["pgrep", "-fl", "ComfyUI|main[.]py --port|[t]rellis|[h]unyuan3d|[P]ixal3D|mflux-generat[e]"], capture_output=True, text=True)
    return f"other GPU processes: {r.stdout.strip()[:200]}" if r.returncode == 0 else ""


def gpu_busy() -> str:
    for pat, what in (("ltx-2-mlx generat[e]", "an LTX render"), ("mflux-generat[e]", "the image model"),
                      ("[d]s4-server", "a ds4 server"), ("[l]lama-server", "a llama server")):
        if subprocess.run(["pgrep", "-f", pat], capture_output=True).returncode == 0:
            return what
    try:
        run = json.load(urllib.request.urlopen("http://127.0.0.1:8090/running", timeout=5)).get("running", [])
        if run:
            return f"llama-swap has {run} loaded"
    except Exception:
        pass
    other = other_gpu_jobs()
    if other:
        return other
    util, mem = gpu_state()
    # a job just finished leaves ~30% utilization in ioreg's window for a few seconds with ~1 GB in use; a foreign job
    # (the ComfyUI Trellis2 job of 2026-09-26) holds many GB
    if util > 60 or mem > 10:
        return f"another process holds the GPU ({util:.0f}% busy, {mem:.1f} GB in use)"
    return ""


def wait_gpu() -> None:
    t0 = time.time()
    while (b := gpu_busy()):
        if time.time() - t0 > 3600:
            sys.exit(f"GPU still busy after an hour: {b}")
        print(f"waiting: {b}", flush=True)
        time.sleep(30)


def render(out: Path, line: str, seed: int, mode: str, size: str, seconds: float, image: Path | None = None,
           extra: list[str] | None = None, dry: bool = False) -> None:
    if out.with_suffix(".json").exists():
        print(f"skip {out.relative_to(OUT)} (done)")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(VIDGEN), "--no-open", "--portrait", "--size", size, "--seconds", str(seconds), "--seed", str(seed),
           "-o", str(out)]
    if mode == "quality":
        cmd.insert(2, "--quality")
    if image:
        cmd += ["-i", str(image)]
    cmd.append(f"{line} {BIBLE}")
    if extra:
        cmd += ["--", *extra]
    print(("DRY " if dry else "") + f"render {out.relative_to(OUT)}: {mode}, seed {seed}, {size}, {seconds} s"
          + (f", image {image.name}" if image else "") + (f", engine {' '.join(extra)}" if extra else ""), flush=True)
    if dry:
        return
    wait_gpu()
    t0 = time.time()
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        sys.exit(f"vidgen failed ({r.returncode}) for {out}")
    print(f"  done in {time.time() - t0:.0f} s", flush=True)


def still(out: Path, prompt: str, seeds: list[int], width: int, height: int, dry: bool = False) -> list[Path]:
    """Qwen-Image-2.1 on mflux, offline, one load for all seeds (rig/keyframe/IMAGE-MODEL.md)."""
    outs = [out.parent / out.name.replace("{seed}", str(s)) for s in seeds]
    todo = [s for s, o in zip(seeds, outs) if not o.exists()]
    if not todo:
        print(f"skip stills {out.name} (done)")
        return outs
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(MFLUX_QWEN), "--prompt", prompt, "--width", str(width), "--height", str(height), "--steps", "40",
           "--seed", *map(str, todo), "--output", str(out), "--metadata"]
    print(("DRY " if dry else "") + f"stills {out.name}: seeds {todo}, {width}x{height}", flush=True)
    if dry:
        return outs
    wait_gpu()
    t0 = time.time()
    r = subprocess.run(cmd, env=dict(os.environ, HF_HUB_OFFLINE="1"), capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(f"mflux failed ({r.returncode})")
    print(f"  {len(todo)} stills in {time.time() - t0:.0f} s", flush=True)
    return outs


def fit(src: Path, dst: Path, w: int, h: int) -> Path:
    """Scale and centre-crop a still to exactly the video's frame size."""
    if not dst.exists():
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vf",
                        f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", str(dst)], check=True)
    return dst


def frame_size(size: str) -> tuple[int, int]:
    return {"480p": (448, 704), "720p": (704, 1280)}[size]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["e1", "e2", "e2q", "stills", "k2", "mstills", "mk2", "boards", "idboards"])
    ap.add_argument("--size", default="480p", choices=["480p", "720p"])
    ap.add_argument("--seconds", type=float, default=5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    d, dry = OUT / a.size, a.dry_run
    if a.step == "e1":
        for mode in ("fast", "quality"):
            for key in ("m5", "m13", "m16"):
                render(d / "e1" / f"{key}-{mode}-s{SEED}.mp4", LINES[key], SEED, mode, a.size, a.seconds, dry=dry)
            for s in (SEED + 1, SEED + 2):
                render(d / "e1" / f"m13-{mode}-s{s}.mp4", LINES["m13"], s, mode, a.size, a.seconds, dry=dry)
    elif a.step in ("e2", "e2q"):
        e2 = d / a.step
        if a.step == "e2":
            render(e2 / "plate.mp4", LINES["plate"], SEED, "fast", a.size, 2, dry=dry)
            plate = e2 / "plate.png"
            if not dry and not plate.exists():
                subprocess.run([str(REPO / "bin/pick-face-frame"), str(e2 / "plate.mp4"), str(plate)], check=True)
        else:
            w, h = frame_size(a.size)
            outs = still(e2 / "marrow-qwen-s{seed}.png", STILLS["marrow"], [SEED], 704, 1104 if a.size == "480p" else 1280, dry)
            plate = fit(outs[0], e2 / "plate.png", w, h) if not dry else e2 / "plate.png"
        render(e2 / f"m16-fast-s{SEED}-noplate.mp4", LINES["m16"], SEED, "fast", a.size, a.seconds, dry=dry)
        for idx in (0, 96):
            for st in (0.2, 0.3, 0.4):
                render(e2 / f"m16-fast-s{SEED}-plate-i{idx}-st{st}.mp4", LINES["m16"], SEED, "fast", a.size, a.seconds,
                       extra=["--image", str(plate), str(idx), str(st)], dry=dry)
    elif a.step == "stills":
        w, h = (704, 1104) if a.size == "480p" else (704, 1280)
        for key in ("coit", "ladies"):
            still(d / "stills" / f"{key}-qwen-s{{seed}}.png", STILLS[key], [1, 2, 3], w, h, dry)
    elif a.step == "k2":
        w, h = frame_size(a.size)
        for key in ("coit", "ladies"):
            render(d / "k2" / f"{key}-quality-s{SEED}-text.mp4", LINES[key], SEED, "quality", a.size, a.seconds, dry=dry)
            pick = d / "stills" / f"{key}-pick.png"   # the chosen still, copied by hand after looking at the three
            if not pick.exists() and not dry:
                sys.exit(f"choose a still first: cp {d}/stills/{key}-qwen-sN.png {pick}")
            first = fit(pick, d / "k2" / f"{key}-first-{w}x{h}.png", w, h) if not dry else pick
            render(d / "k2" / f"{key}-quality-s{SEED}-still.mp4", LINES[key], SEED, "quality", a.size, a.seconds,
                   image=first, dry=dry)
    elif a.step == "mstills":
        w, h = (704, 1104) if a.size == "480p" else (704, 1280)
        for key, prompt in MSHOTS.items():
            still(d / "mstills" / f"{key}-qwen-s{{seed}}.png", prompt, [SEED], w, h, dry)
    elif a.step == "mk2":
        w, h = frame_size(a.size)
        for key in MSHOTS:
            src = d / "mstills" / f"{key}-qwen-s{SEED}.png"
            first = fit(src, d / "mk2" / f"{key}-first-{w}x{h}.png", w, h) if not dry else src
            render(d / "mk2" / f"{key}-fast-s{SEED}-still.mp4", LINES[key], SEED, "fast", a.size, a.seconds, image=first, dry=dry)
    elif a.step == "idboards":
        # Marrow's face per clip (rig/review_images.py board): one board per E1 mode, one per E2 variant
        sys.path.insert(0, str(REPO / "rig"))
        import review_images as RI
        for sub, groups in (("e1", {"fast": "*-fast-*.mp4", "quality": "*-quality-*.mp4"}),
                            ("e2", {"plate": "*.mp4"}), ("e2q", {"plate": "*.mp4"})):
            for gname, pat in groups.items():
                clips = sorted((d / sub).glob(pat))
                clips = [c for c in clips if c.stem != "plate"] if sub.startswith("e2") else clips
                if not clips:
                    continue
                tiles = [(c.stem.replace("-s1031", "").replace("m16-fast-", ""), c, "largest") for c in clips]
                if sub.startswith("e2") and (d / sub / "plate.png").exists():
                    tiles.insert(0, ("the plate", d / sub / "plate.mp4" if (d / sub / "plate.mp4").exists() else None, "largest"))
                    tiles = [t for t in tiles if t[1] is not None]
                out = d / f"idboard-{sub}-{gname}.png"
                RI.board(out, f"Marrow, {sub} {gname}", tiles)
                print(out)
    elif a.step == "boards":
        for sub in ("e1", "e2", "e2q"):
            clips = sorted((d / sub).glob("*.mp4"))
            if not clips:
                continue
            sheet = d / f"{sub}-sheet.png"
            ins, filt = [], ""
            for i, c in enumerate(clips):
                ins += ["-i", str(c)]
                filt += f"[{i}:v]fps=4/{a.seconds},scale=200:-2,tile=4x1[r{i}];"
            filt += "".join(f"[r{i}]" for i in range(len(clips))) + f"vstack=inputs={len(clips)}" if len(clips) > 1 else "[r0]null"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins, "-filter_complex", filt,
                            "-frames:v", "1", str(sheet)], check=True)
            print(sheet, "rows:", ", ".join(c.stem for c in clips))


if __name__ == "__main__":
    main()
