#!/usr/bin/env python3
"""summarize.py — one row per condition from results.jsonl (shot lab): first-take sync verdicts, offsets, confidence,
face size at the line, and for exchanges the per-line attribution. Writes summary.md."""
import json, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
NAMES = {"C0": "medium close-up (control)", "F1": "waist up", "F2": "knees up", "F3": "full length ([cast])",
         "F4": "wide ([cast])", "F4n": "wide, no [cast]", "F5n": "extreme wide, no [cast]", "F3n": "full length, no [cast]",
         "P1": "two-shot, silent listener", "P2": "two-person exchange in one shot", "P4": "over the shoulder",
         "A1": "profile", "M1": "walk-and-talk toward camera", "M2": "walk-and-talk, dolly alongside",
         "O1": "handheld mic at the mouth", "O3": "laughing through the line", "T1": "speech from frame 0",
         "T2": "3 words in 8 s", "F4L": "wide, [cast] [layout]", "F5L": "extreme wide, [cast] [layout]",
         "F3L": "full length, [cast] [layout]", "L1": "landscape waist up", "L2": "landscape wide",
         "P3": "group of four, one speaks", "M3": "orbiting camera", "O2": "coffee sip, then the line",
         "T3": "29 words in 8 s", "V1": "shouting", "V2": "whispering", "K1": "painted clown",
         "H1": "wide + 'stays planted' wording", "H2": "wide + [hold]", "H3": "wide, seated + [hold]",
         "H4": "wide + [cast] [layout] [hold]", "H5": "wide exchange + [hold]"}
rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines()]
by = collections.OrderedDict()
for r in rows: by.setdefault((r["project"], r["cond"]), []).append(r)
out = ["| condition | clips | in sync (first take) | offsets ms | conf | face px at the line |", "|---|---|---|---|---|---|"]
tot = ok = 0
for (proj, cid), rs in by.items():
    n = len(rs); good = 0; offs = []; confs = []; px = []
    for r in rs:
        g, a = r["gate"], r["attribution"]
        if len(r["lines"]) > 1:   # an exchange: per-line attribution (the v3 gate's exchange path)
            ls = a.get("lines", [])
            fine = len(ls) == len(r["lines"]) and all(L["speaker"] and L["speaker"]["conf"] >= 4.2 for L in ls) \
                and len({L["speaker"]["track"] for L in ls}) == len(ls)
            good += fine; offs += [L["speaker"]["offset_ms"] for L in ls if L["speaker"]]
            confs += [L["speaker"]["conf"] for L in ls if L["speaker"]]
        else:
            good += g.get("verdict") == "PASS"; offs.append(g.get("offset_ms")); confs.append(g.get("conf"))
        px.append(g.get("face_px"))
    tot += n; ok += good
    rng = lambda v: f"{min(v)}..{max(v)}" if v and None not in v else str(v)
    out.append(f"| {NAMES.get(cid, cid)} ({cid}) | {n} | {good}/{n} | {rng(offs)} | {rng(confs)} | {rng(px)} |")
out.append(f"\n**{ok} of {tot} first takes in sync** (an exchange counts when each line comes from its own face at "
           "conf >= 4.2).")
(HERE / "summary.md").write_text("\n".join(out) + "\n"); print("\n".join(out))
