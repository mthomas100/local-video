#!/usr/bin/env python3
"""review_images.py — the images a director reviews: one labelled image per clip, identity boards (2026-09-26).

Why one image per clip: ds4's DeepSeek V4 vision path gives every image at most 381 tokens of 42x42 px cells
(ds4_image.c, ds4_deepseek4_safe_resize). On a contact sheet of 6 rows x 4 frames each frame reached the model at
about 200x112 px; a clip's 4 frames in a 2x2 grid reach it at about 520x285 each.
Why the label is drawn into the image: pi sends a tool result's text as the `tool` message and all its images
together in one trailing `user` message, so a text label cannot sit next to its image.
Frames are taken the way skills/film/scripts/sheet.sh takes them (ffmpeg fps=k/duration). CPU only (ffmpeg,
PIL, macOS Vision on the CPU through bin/facebox.swift). Used by rig/film-rig.ts (review_scenes) and by
rig/bench/review-bench.py, so both show the model the same pictures.

  review_images.py grid <clip.mp4> <out.png> <label>            one clip, 2x2, label strip on top
  review_images.py grids <film dir> <scene>...                   <film>/.review/clip-N.png for each scene, "clip N",
                                                                 remade only when the clip is newer; prints the paths
  review_images.py board <out.png> <title> <label>=<clip.mp4>[@left|@right]...   an identity board
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # /opt/homebrew python has no PIL; the engine's venv does (no MLX import here)
    venv = Path.home() / "repos/ltx-2-mlx/.venv/bin/python"
    if venv.exists() and os.environ.get("REVIEW_IMAGES_REEXEC") != "1":
        os.environ["REVIEW_IMAGES_REEXEC"] = "1"
        os.execv(str(venv), [str(venv), __file__, *sys.argv[1:]])
    raise

REPO = Path(__file__).resolve().parents[1]
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
STRIP = 44


def font(size: int):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 8.0


def frames(clip: Path, k: int, fps: str | None = None) -> list[Image.Image]:
    """k frames spread over the clip (sheet.sh's timestamps), or every frame at `fps`."""
    with tempfile.TemporaryDirectory() as t:
        vf = f"fps={k}/{duration(clip)}" if fps is None else f"fps={fps}"
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip), "-vf", vf]
        if fps is None:
            args += ["-frames:v", str(k)]
        subprocess.run(args + [str(Path(t) / "f-%03d.png")], check=True)
        return [Image.open(p).convert("RGB") for p in sorted(Path(t).glob("f-*.png"))]


def with_strip(img: Image.Image, label: str) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + STRIP), (255, 255, 255))
    out.paste(img, (0, STRIP))
    ImageDraw.Draw(out).text((10, 7), label, fill=(0, 0, 0), font=font(30))
    return out


def grid(clip: Path, out: Path, label: str) -> Path:
    """The clip's 4 frames at half size in a 2x2 grid (left to right, then top to bottom), 6 px white gaps, and a
    label strip on top."""
    fr = frames(clip, 4)
    w, h = fr[0].width // 2, fr[0].height // 2
    g = Image.new("RGB", (w * 2 + 6, h * 2 + 6), (255, 255, 255))
    for j, f in enumerate(fr[:4]):
        g.paste(f.resize((w, h), Image.BICUBIC), ((j % 2) * (w + 6), (j // 2) * (h + 6)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with_strip(g, label).save(out)
    return out


def previous_take(film: Path, n: str) -> Path | None:
    """The latest earlier take of scene n (redo-K/scene-n.mp4 with the highest K), or None."""
    ks = sorted((int(d.name.split("-")[1]), d) for d in film.glob("redo-*") if d.name.split("-")[1].isdigit()
                and (d / f"scene-{n}.mp4").exists())
    return ks[-1][1] / f"scene-{n}.mp4" if ks else None


def pair(old: Path, new: Path, out: Path, label: str) -> Path:
    """A redone clip against its previous take (2026-09-27): top row two frames of the PREVIOUS take (at 1/3 and 2/3),
    bottom row the same moments of the NEW take, so the director can keep the better one; same size per frame as a
    2x2 grid. On 2026-09-26 the redo review saw only new takes and kept a worse shot 13."""
    rows = []
    for c in (old, new):
        fr = frames(c, 4)
        rows.append([fr[1], fr[2]] if len(fr) >= 3 else fr[:2])
    w, h = rows[0][0].width // 2, rows[0][0].height // 2
    g = Image.new("RGB", (w * 2 + 6, h * 2 + 40 + 6), (255, 255, 255))
    d = ImageDraw.Draw(g)
    for r, (fr, tag) in enumerate(zip(rows, ("PREVIOUS take", "NEW take"))):
        y = r * (h + 20 + 6)
        d.text((8, y), tag, fill=(180, 0, 0) if r == 0 else (0, 110, 0), font=font(18))
        for j, f in enumerate(fr[:2]):
            g.paste(f.resize((w, h), Image.BICUBIC), (j * (w + 6), y + 20))
    out.parent.mkdir(parents=True, exist_ok=True)
    with_strip(g, label).save(out)
    return out


def faceboxes(paths: list[Path]) -> list[dict]:
    r = subprocess.run(["swift", str(REPO / "bin/facebox.swift"), *map(str, paths)], capture_output=True, text=True)
    return [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]


def best_face(clip: Path, pick: str = "largest") -> tuple[Image.Image, tuple[float, float, float, float] | None]:
    """The frame (sampled at 2 fps) whose chosen face has the best Vision quality x area, and a head-and-shoulders
    box around that face; pick = largest | left | right (for a clip with two people)."""
    with tempfile.TemporaryDirectory() as t:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip), "-vf", "fps=2",
                        str(Path(t) / "f-%03d.png")], check=True)
        paths = sorted(Path(t).glob("f-*.png"))
        best = None
        for b in faceboxes(paths):
            fs = b["faces"]
            if not fs:
                continue
            f = (min(fs[:2], key=lambda f: f["x"]) if pick == "left" and len(fs) > 1 else
                 max(fs[:2], key=lambda f: f["x"]) if pick == "right" and len(fs) > 1 else fs[0])
            s = f["q"] * f["w"] * f["h"]
            if best is None or s > best[0]:
                best = (s, b["path"], f)
        if best is None:
            img = Image.open(paths[len(paths) // 2]).convert("RGB")
            return img, None
        img = Image.open(best[1]).convert("RGB")
        f = best[2]
        return img, (f["x"], f["y"], f["w"], f["h"])


def board(out: Path, title: str, tiles: list[tuple[str, Path, str]], tw: int = 300, th: int = 360) -> Path:
    """One character's identity board: a head-and-shoulders crop per clip, labelled, 3 tiles a row, the character's
    name in a strip on top. tiles = [(label, clip, pick)]."""
    ims = []
    for lab, clip, pick in tiles:
        img, f = best_face(clip, pick)
        if f is None:
            box = (img.width * 0.3, img.height * 0.1, img.width * 0.7, img.height * 0.9)
        else:
            x, y, w, h = f
            bw = w * 2.6
            bh = bw * th / tw
            top = max(0, y - h * 0.7)
            box = (max(0, x + w / 2 - bw / 2), top, min(img.width, x + w / 2 + bw / 2), min(img.height, top + bh))
        crop = img.crop(tuple(int(v) for v in box))
        crop.thumbnail((tw, th - 28), Image.LANCZOS)
        tile = Image.new("RGB", (tw, th), (255, 255, 255))
        tile.paste(crop, ((tw - crop.width) // 2, 28 + (th - 28 - crop.height) // 2))
        ImageDraw.Draw(tile).text((8, 2), lab, fill=(0, 0, 0), font=font(22))
        ims.append(tile)
    cols = min(3, len(ims))
    rows = -(-len(ims) // cols)
    b = Image.new("RGB", (cols * tw + (cols - 1) * 8, rows * th + (rows - 1) * 8), (200, 200, 200))
    for j, t in enumerate(ims):
        b.paste(t, ((j % cols) * (tw + 8), (j // cols) * (th + 8)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with_strip(b, title).save(out)
    return out


def main() -> None:
    a = sys.argv[1:]
    if a[:1] == ["grid"] and len(a) == 4:
        print(grid(Path(a[1]), Path(a[2]), a[3]))
    elif a[:1] == ["grids"] and len(a) >= 3:
        film = Path(a[1])
        for n in a[2:]:
            clip, out = film / f"scene-{n}.mp4", film / ".review" / f"clip-{n}.png"
            if not out.exists() or out.stat().st_mtime < clip.stat().st_mtime:
                grid(clip, out, f"clip {n}")
            print(out)
    elif a[:1] == ["pairs"] and len(a) >= 3:
        film = Path(a[1])
        for n in a[2:]:
            clip, out = film / f"scene-{n}.mp4", film / ".review" / f"pair-{n}.png"
            old = previous_take(film, n)
            if old is None:
                print(f"no previous take of {n}", file=sys.stderr); continue
            if not out.exists() or out.stat().st_mtime < max(clip.stat().st_mtime, old.stat().st_mtime):
                pair(old, clip, out, f"clip {n}: previous vs new take")
            print(out)
    elif a[:1] == ["board"] and len(a) >= 4:
        tiles = []
        for spec in a[3:]:
            lab, _, rest = spec.partition("=")
            clip, _, pick = rest.partition("@")
            tiles.append((lab, Path(clip), pick or "largest"))
        print(board(Path(a[1]), a[2], tiles))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
