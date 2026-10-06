#!/usr/bin/env python3
"""lab_report.py <project.txt>... — the shot lab's results by condition (2026-10-03).

For every scene of each lab project:
- the condition and seed, from the project's "#   scene N: ID seed S" index;
- the gate's own verdict (meter v3) from ~/Videos/vidgen/<NAME>/sync-N.json, written while pi rendered;
- attribution.py: per quoted line, whose face follows the voice (screen x, face px, conf, offset) and any second
  mouth on screen at the same time;
- a full-frame strip with the speaker boxed (green) and second mouths (red), in strips/.

Writes results.jsonl and results.md (one row per condition) next to this script. CPU only, resumable.
"""
import json, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(Path.home() / "repos/local-video/rig"))
from dialogue import quoted_lines
from attribution import attribute
sys.path.insert(0, str(Path.home() / "repos/local-video/rig/sync"))

VID = Path.home() / "Videos/vidgen"


def scenes_of(proj: Path):
    t = proj.read_text()
    name = re.search(r"^NAME=([\w-]+)", t, re.M).group(1)
    index = {int(m.group(1)): (m.group(2), int(m.group(3))) for m in re.finditer(r"#\s+scene\s+(\d+): (\w+) seed (\d+)", t)}
    lines = re.findall(r'^"(.*)"\s*$', t, re.M)
    return name, [(n, *index[n], lines[n - 1]) for n in sorted(index)]


def main(projs):
    out = HERE / "results.jsonl"
    done = {json.loads(l)["key"] for l in out.read_text().splitlines()} if out.exists() else set()
    with out.open("a") as fo:
        for p in projs:
            name, scenes = scenes_of(Path(p))
            for n, cid, seed, text in scenes:
                key = f"{name}:{n}"
                if key in done: continue
                clip = VID / name / f"scene-{n}.mp4"
                import time
                if not clip.exists() or not clip.with_suffix(".json").exists() or time.time() - clip.stat().st_mtime < 30:
                    continue   # not rendered yet, or still being written
                g = VID / name / f"sync-{n}.json"
                gate = json.loads(g.read_text()) if g.exists() else {}
                ql = quoted_lines(text)
                if not gate:   # the lab renders with SYNC_GATE=off (no GPU idle while the CPU measures): measure here
                    import syncmeter
                    try: gate = syncmeter.measure(clip, " ".join(ql), one_line=len(ql) == 1)
                    except Exception as e: gate = {"verdict": "ERROR", "why": repr(e)}
                try:
                    strips = VID / name / "strips"; strips.mkdir(exist_ok=True)   # media stays out of git
                    att = attribute(clip, ql, strips / f"{name}-{n}-{cid}-{seed}.jpg")
                except Exception as e:
                    att = {"error": repr(e)}
                row = {"key": key, "project": name, "scene": n, "cond": cid, "seed": seed, "lines": ql,
                       "gate": {k: gate.get(k) for k in ("meter", "verdict", "why", "cause", "offset_ms", "conf",
                                                          "face_px", "face_h", "coverage", "detect_scale",
                                                          "other_mouths", "words", "words_weak", "onset_s",
                                                          "faces_max")},
                       "attribution": att}
                fo.write(json.dumps(row) + "\n"); fo.flush()
                print(f"{key} {cid} seed {seed}: gate {gate.get('verdict')} {gate.get('offset_ms')} ms conf "
                      f"{gate.get('conf')} face {gate.get('face_px')} px", flush=True)
    table()


def table():
    rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines()]
    by = {}
    for r in rows: by.setdefault((r["project"], r["cond"]), []).append(r)
    md = ["| project | cond | seed | gate verdict | offset ms | conf | face px | speaker x per line | 2nd mouth |",
          "|---|---|---|---|---|---|---|---|---|"]
    for (proj, cid), rs in by.items():
        for r in sorted(rs, key=lambda r: r["seed"]):
            g, a = r["gate"], r["attribution"]
            sp = "; ".join(f'{(L["speaker"] or {}).get("x")} ({(L["speaker"] or {}).get("conf")})' for L in a.get("lines", []))
            also = "; ".join(str([q["x"] for q in L["also"]]) for L in a.get("lines", []) if L["also"]) or "-"
            md.append(f'| {proj} | {cid} | {r["seed"]} | {g.get("verdict")} {("(" + (g.get("why") or "") + ")") if g.get("verdict") != "PASS" else ""} '
                      f'| {g.get("offset_ms")} | {g.get("conf")} | {g.get("face_px")} | {sp or a.get("error", "-")} | {also} |')
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    if sys.argv[1:] == ["--table"]: table()
    else: main(sys.argv[1:])
