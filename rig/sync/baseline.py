#!/usr/bin/env python3
"""baseline.py — the dialogue-sync baseline table from rig/sync/backmeasure.py output, with the CURRENT meter rules
(syncmeter.verdict re-applied to the stored measurements, so a threshold change needs no re-measure). 2026-09-27.

  baseline.py <rows.jsonl>...     markdown: per film, one row per dialogue shot (final cut, raw, earlier takes), the
                                  final-cut pass rate, the raw-to-final offset change (the pipeline's), offsets
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import syncmeter  # noqa: E402

CAUSE = {"M1": "offset", "M3": "mouth does not follow / no sync peak", "V1": "speaker not visible", "W": "line not spoken"}


def rev(r):
    if "coverage" in r and r.get("verdict") != "NO-SPEECH":
        r = {**r}; r.pop("cause", None); r.update(syncmeter.verdict({**r, "verdict": None}))
    return r


for f in sys.argv[1:]:
    rows = [rev(json.loads(l)) for l in open(f) if l.strip()]
    if not rows: continue
    film = rows[0]["film"]
    print(f"\n### {film} (meter {syncmeter.METER_VERSION})\n")
    print("| shot | line | final cut | raw clip | final - raw (ms) | earlier takes |")
    print("|---|---|---|---|---|---|")
    shots = sorted({r["scene"] for r in rows})
    fin_pass = 0; deltas = []
    for n in shots:
        rs = [r for r in rows if r["scene"] == n]
        def cell(r):
            if not r: return "-"
            v = r.get("verdict", "ERR")
            s = f"**{v}**" if v != "PASS" else v
            if "offset_ms" in r: s += f" {r['offset_ms']:+d} ms, conf {r['conf']}"
            if r.get("cause"): s += f" ({CAUSE.get(r['cause'], r['cause'])})"
            return s
        fi = next((r for r in rs if r["kind"] == "final"), None)
        ra = next((r for r in rs if r["kind"] == "raw"), None)
        tk = [r for r in rs if r["kind"].startswith("take")]
        if fi and fi.get("verdict") == "PASS": fin_pass += 1
        d = (fi["offset_ms"] - ra["offset_ms"]) if fi and ra and "offset_ms" in fi and "offset_ms" in ra else None
        if d is not None: deltas.append(d)
        print(f"| {n} | {rs[0]['line'][:48]} | {cell(fi)} | {cell(ra)} | {'' if d is None else f'{d:+d}'} | "
              f"{'; '.join(r['kind'].split(':')[1] + ': ' + cell(r) for r in tk)} |")
    offs = [r["offset_ms"] for r in rows if r["kind"] == "raw" and "offset_ms" in r and r.get("conf", 0) >= 5]
    print(f"\nFinal cut: {fin_pass}/{len(shots)} dialogue shots PASS. Raw clip offsets (conf >= 5): "
          f"median {sorted(offs)[len(offs)//2] if offs else '-'} ms, range {min(offs) if offs else '-'}..{max(offs) if offs else '-'}. "
          f"Final minus raw: {', '.join(f'{x:+d}' for x in deltas)} ms.")
