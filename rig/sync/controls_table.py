#!/usr/bin/env python3
"""controls_table.py — score a sync meter's JSONL output on rig/sync/make_controls.py folders (2026-09-27).
  controls_table.py <meter.jsonl>   per source: base offset of shift0, each planted shift's recovered offset and error
  (ms, relative to shift0; the meter's sign: + = audio early), its verdict, and the swap/hidden/frozen verdicts;
  then the acceptance summary of `docs/dialogue-sync.md`"""
import json, re, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
if "--reverdict" in sys.argv:   # apply the current syncmeter.verdict() to stored measurements (run with the sync venv)
    sys.path.insert(0, __import__("os").path.dirname(__file__)); import syncmeter
    for r in rows:
        if r.get("verdict") not in ("NO-SPEECH",) and "coverage" in r:
            r.pop("cause", None); r.update(syncmeter.verdict({**r, "verdict": None}))
by = {}
for r in rows:
    parts = r["clip"].split("/")
    by.setdefault(parts[-2], {})[parts[-1]] = r
errs, calls = [], {"swap": [], "hidden": [], "frozen": []}
det = {}
for src, d in by.items():
    base = d.get("shift0ms.mp4", {}).get("offset_ms")
    out = []
    shifts = sorted((f for f in d if f.startswith("shift")), key=lambda f: int(re.search(r"shift([+-]?\d+)", f).group(1)))
    for f in shifts:
        r = d[f]; planted = -int(re.search(r"shift([+-]?\d+)", f).group(1))   # make_controls: + = audio delayed
        o = r.get("offset_ms")
        e = None if (o is None or base is None) else (o - base) - planted
        if e is not None: errs.append(abs(e))
        v = r.get("verdict", "?")
        det.setdefault(abs(planted), []).append(v != "PASS")
        out.append(f"{planted:+d}→{o if o is not None else '-'}({'' if e is None else f'{e:+d}'}) {v[:4]} c{r.get('conf')}")
    for k in calls:
        f = f"{k}.mp4"
        if f in d:
            calls[k].append(d[f].get("verdict")); out.append(f"{k}: {d[f].get('verdict')} c{d[f].get('conf')}")
    print(f"{src} (shift0 offset {base} ms, face {d.get('shift0ms.mp4', {}).get('face_h')})")
    print("   " + " | ".join(out))
print(f"\nshift recovery: {len(errs)} planted shifts, |error| max {max(errs) if errs else '-'} ms, "
      f"within 42 ms: {sum(e <= 42 for e in errs)}/{len(errs)}")
print("flagged (not PASS) by |planted|: " + ", ".join(f"{k} ms {sum(v)}/{len(v)}" for k, v in sorted(det.items())))
for k, v in calls.items(): print(f"{k}: {v}")
