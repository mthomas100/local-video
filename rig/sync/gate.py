#!/usr/bin/env python3
"""gate.py — the dialogue-sync gate (2026-09-27, iteration 5; `docs/dialogue-sync.md`). Local, CPU.

Sync is enforced by the rig, not judged by the director: the director reviews silent stills and cannot perceive sync.
Every clip whose scene line has a quoted spoken line is measured by rig/sync/syncmeter.py, and the result is kept
next to the clip as sync-N.json (tied to that exact take: size, mtime, meter version, thresholds, line).

  gate.py <film> [scene ...]              measure (cached) and print one verdict line per dialogue scene
  gate.py stitch-check <film> <n-scenes>  exit 1, listing the shots, when a dialogue shot is not PASS and has no
                                          acceptance for its current take (story.sh refuses to stitch then)
  gate.py accept <film> <scene> <reason>  the director's recorded exception for the current take of a shot
                                          (keep_take accept_sync_fail); it goes into sync-report.txt
  gate.py best <film> <scene>             after the retakes: put the best take (by verdict, then confidence) back
  gate.py report <film> <n-scenes>        write and print $OUT/sync-report.txt (every dialogue shot's verdict and
                                          every exception), for the final report

Scene tokens: [offscreen] marks a line spoken by someone not in frame (the F6 fallback: turned away, a reaction
shot, a wide). It is not gated for lip sync; only the words are checked by the pre-check's transcript.
SYNC_GATE=report (env) keeps the verdicts but never refuses a stitch.
"""
from __future__ import annotations
import hashlib, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import syncmeter  # noqa: E402  (re-execs into the sync venv when needed)
from dialogue import quoted_lines  # noqa: E402

VIDEOS = Path.home() / "Videos/vidgen"


def scene_texts(out: Path) -> list[str]:
    p = out / "project.txt"
    if not p.exists(): return []
    txt = p.read_text()
    m = re.search(r"^SCENES=\(\s*\n(.*?)^\)", txt, re.M | re.S)
    return re.findall(r'^"(.*)"$', m.group(1) if m else txt, re.M)


def tokens_and_line(text: str) -> tuple[set[str], str]:
    toks = set()
    while text.startswith("["):
        t, _, text = text.partition("] ")
        toks.add(t.lstrip("[").split("=")[0])
    return toks, text


def take_key(clip: Path, line: str) -> str:
    st = clip.stat()
    th = hashlib.sha1(json.dumps(syncmeter.THRESH, sort_keys=True).encode()).hexdigest()[:8]
    return f"{syncmeter.METER_VERSION}:{th}:{st.st_size}:{st.st_mtime_ns}:" + hashlib.sha1(line.encode()).hexdigest()[:10]


def gate_scene(out: Path, n: int, text: str, fresh: bool = False) -> dict | None:
    """The gate result for scene n's current clip, or None when the scene has no spoken line."""
    toks, body = tokens_and_line(text)
    lines = quoted_lines(body)
    if not lines: return None
    clip = out / f"scene-{n}.mp4"
    if not clip.exists(): return {"scene": n, "verdict": "MISSING", "line": " ".join(lines)}
    if "offscreen" in toks:
        return {"scene": n, "verdict": "OFFSCREEN", "line": " ".join(lines)}
    line = " ".join(lines)
    key = take_key(clip, line)
    jf = out / f"sync-{n}.json"
    if not fresh and jf.exists():
        try:
            r = json.loads(jf.read_text())
            if r.get("key") == key: return r
        except json.JSONDecodeError: pass
    from dialogue import line_speakers
    r = syncmeter.measure(clip, line, one_line=len(lines) == 1, lines=lines if len(lines) > 1 else None,
                          speakers=line_speakers(body) if len(lines) > 1 else None)
    r.update({"scene": n, "key": key, "line": line})
    jf.write_text(json.dumps(r) + "\n")
    return r


def accepted(out: Path, r: dict) -> str | None:
    f = out / f"sync-accept-{r['scene']}.json"
    if not f.exists(): return None
    a = json.loads(f.read_text())
    return a["reason"] if a.get("key") == r.get("key") else None


def verdict_line(r: dict, out: Path | None = None) -> str:
    n = r["scene"]
    if r["verdict"] == "MISSING": return f"sync {n}: MISSING (no clip yet)"
    if r["verdict"] == "OFFSCREEN": return f"sync {n}: OFFSCREEN voice (not lip-synced; words checked by the transcript)"
    s = syncmeter.line_of(str(n), r)
    why = accepted(out, r) if out else None
    return s + (f" (ACCEPTED by the director: {why})" if why else "")


def blocking(out: Path, n_scenes: int) -> list[tuple[dict, str]]:
    texts = scene_texts(out)
    bad = []
    for n in range(1, n_scenes + 1):
        r = gate_scene(out, n, texts[n - 1] if n - 1 < len(texts) else "")
        if r is None or r["verdict"] in ("PASS", "OFFSCREEN"): continue
        if r["verdict"] in ("FAIL", "UNMEASURABLE", "NO-SPEECH") and accepted(out, r): continue
        bad.append((r, verdict_line(r, out)))
    return bad


def main(argv: list[str]) -> int:
    if not argv: print(__doc__); return 2
    if argv[0] == "stitch-check":
        out = VIDEOS / argv[1]
        bad = blocking(out, int(argv[2]))
        for _, l in bad: print(l)
        if bad and os.environ.get("SYNC_GATE", "enforce") != "report":
            print(f"SYNC GATE: {len(bad)} dialogue shot(s) not in sync; not stitching. Retake them (redo_scenes: a new "
                  f"[seed=N], the speaker's face larger, the line after a beat), make the line [offscreen], or record an "
                  f"exception with keep_take accept_sync_fail.")
            return 1
        return 0
    if argv[0] == "accept":
        out = VIDEOS / argv[1]; n = int(argv[2]); reason = " ".join(argv[3:]).strip()
        if not reason: print("accept needs a reason"); return 2
        texts = scene_texts(out)
        r = gate_scene(out, n, texts[n - 1])
        if r is None: print(f"scene {n} has no spoken line; nothing to accept"); return 1
        (out / f"sync-accept-{n}.json").write_text(json.dumps({"scene": n, "key": r.get("key"), "reason": reason,
                                                                "verdict": verdict_line(r)}) + "\n")
        print(f"scene {n}: sync exception recorded for this take: {reason}"); return 0
    if argv[0] == "best":
        # after SYNC_TRIES takes with no PASS: keep the best take (story.sh). Rank: PASS, then an offset-only FAIL
        # (the mouth follows the voice), then the rest; ties by SyncNet confidence.
        out = VIDEOS / argv[1]; n = int(argv[2])
        def rank(r): return ({"PASS": 3, "FAIL": 1 + (r.get("cause") == "M1"), "UNMEASURABLE": 0}.get(r.get("verdict"), -1),
                             r.get("conf") or 0)
        cur = json.loads((out / f"sync-{n}.json").read_text())
        prompt = json.loads((out / f"scene-{n}.json").read_text()).get("prompt")
        best, bf = cur, None
        for jf in sorted((out / "takes").glob(f"sync-{n}-try*.json")):
            # only takes of the current prompt: an earlier line's takes must never come back (2026-09-27)
            side = out / "takes" / f"scene-{n}-try{jf.stem.split('-try')[1]}.json"
            if not side.exists() or json.loads(side.read_text()).get("prompt") != prompt: continue
            r = json.loads(jf.read_text())
            if rank(r) > rank(best): best, bf = r, jf
        if bf is None:
            print(f"scene {n}: kept the last take ({cur.get('verdict')}, conf {cur.get('conf')})"); return 0
        k = bf.stem.split("-try")[1]
        m = 1 + max([int(x.stem.split("-try")[1]) for x in (out / "takes").glob(f"sync-{n}-try*.json")] + [0])
        for src, dst in ((f"scene-{n}.mp4", f"scene-{n}-try{m}.mp4"), (f"scene-{n}.json", f"scene-{n}-try{m}.json"),
                         (f"sync-{n}.json", f"sync-{n}-try{m}.json")):
            (out / src).rename(out / "takes" / dst)
        for src, dst in ((f"scene-{n}-try{k}.mp4", f"scene-{n}.mp4"), (f"scene-{n}-try{k}.json", f"scene-{n}.json"),
                         (f"sync-{n}-try{k}.json", f"sync-{n}.json")):
            (out / "takes" / src).rename(out / dst)
        print(f"scene {n}: no take passed; kept take {k} ({best.get('verdict')}, conf {best.get('conf')}): "
              + verdict_line(best, out)); return 0
    if argv[0] == "report":
        out = VIDEOS / argv[1]; texts = scene_texts(out)
        rows = [gate_scene(out, n, texts[n - 1]) for n in range(1, int(argv[2]) + 1)]
        rows = [r for r in rows if r]
        passed = sum(r["verdict"] == "PASS" for r in rows)
        gated = sum(r["verdict"] not in ("OFFSCREEN",) for r in rows)
        txt = [f"Dialogue sync gate (meter {syncmeter.METER_VERSION}, thresholds {json.dumps(syncmeter.THRESH)}): "
               f"{passed}/{gated} on-screen dialogue shots PASS"] + [verdict_line(r, out) for r in rows]
        (out / "sync-report.txt").write_text("\n".join(txt) + "\n"); print("\n".join(txt)); return 0
    out = VIDEOS / argv[0]
    texts = scene_texts(out)
    scenes = [int(x) for x in argv[1:]] or list(range(1, len(texts) + 1))
    for n in scenes:
        r = gate_scene(out, n, texts[n - 1] if n - 1 < len(texts) else "", fresh="--fresh" in os.environ.get("SYNC_OPTS", ""))
        if r: print(verdict_line(r, out), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
