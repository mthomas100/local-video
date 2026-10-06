#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""make_charts.py — the README charts, drawn only from the measured rows in docs/data/ (2026-10-05).

    docs/charts/make_charts.py          # writes docs/media/chart-*.png

Every number comes from a file under docs/data/; nothing is typed in here except the screenplay bench table, which
is parsed from rig/bench/screenplay/results.md. Failures are drawn, not dropped.
"""
import csv, json, re
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

ROOT = Path(__file__).resolve().parents[2]
DATA, OUT = ROOT / "docs/data", ROOT / "docs/media"

# the reference palette (light mode); identity is never colour alone: FAIL marks are also a different shape
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10.5,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def rows(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def caption(fig, text):
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=8.5, color=INK2, wrap=True)


def save(fig, name):
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)
    print("wrote", OUT / name)


# ---------- 1. the sync meter on planted truth ----------
def calibration():
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.15, 1]})
    for fname, label, colour, marker in [("meter-v1-controls.jsonl", "LTX clips from our films (5 sources)", BLUE, "o"),
                                         ("meter-v1-ravdess.jsonl", "RAVDESS actors, real speech (6 sources)", ORANGE, "s")]:
        by_src = defaultdict(dict)
        for r in rows(DATA / "sync-calibration" / fname):
            src, kind = r["clip"].split("/")[-2:]
            by_src[src][kind[:-4]] = r
        xs, ys = [], []
        for src, d in by_src.items():
            base = d.get("shift0ms", {}).get("offset_ms")
            if base is None:
                continue
            for kind, r in d.items():
                m = re.fullmatch(r"shift([+-]\d+)ms", kind)
                if m and r.get("offset_ms") is not None:
                    xs.append(-int(m.group(1)))          # make_controls: "+" = audio delayed, the meter's "+" = audio early
                    ys.append(r["offset_ms"] - base)
        err = [y - x for x, y in zip(xs, ys)]
        nudge = -7 if marker == "o" else 7                # side by side, so neither set hides the other
        a.scatter([x + nudge for x in xs], err, s=46, color=colour, marker=marker, edgecolor=SURFACE, linewidth=1.2,
                  zorder=3, label=f"{label}: {len(xs)} non-zero shifts, worst |error| {max(map(abs, err))} ms")
    a.axhspan(-42, 42, color="#eef3fb", zorder=1)
    a.text(-430, 36, "one frame at 24 fps (42 ms)", fontsize=8.5, color=INK2, va="top")
    a.axhline(0, color=INK2, linewidth=1, zorder=2)
    a.set_ylim(-80, 60)
    a.set(xlabel="planted offset (ms, + = voice early)", ylabel="recovered minus planted (ms)",
          title="Planted offsets are recovered within 10 ms")
    a.legend(loc="lower left", fontsize=8.5, frameon=False)

    # confidence by control type: what passes the 4.2 bar and what does not
    groups = defaultdict(list)
    for fname in ("meter-v1-controls.jsonl", "meter-v1-ravdess.jsonl"):
        for r in rows(DATA / "sync-calibration" / fname):
            kind = r["clip"].split("/")[-1][:-4]
            if r.get("conf") is None:
                continue
            g = "in sync (shift 0)" if kind == "shift0ms" else "frozen mouth" if kind == "frozen" else \
                "voice swapped" if kind == "swap" else None
            if g:
                groups[g].append(r["conf"])
    order = ["in sync (shift 0)", "voice swapped", "frozen mouth"]
    for i, g in enumerate(order):
        v = groups[g]
        colour, marker = (BLUE, "o") if i == 0 else (RED, "X")
        b.scatter(v, [i] * len(v), s=60, color=colour, marker=marker, edgecolor=SURFACE, linewidth=1, zorder=3)
        b.text(max(v) + 0.25, i + 0.18, f"n={len(v)}", va="center", fontsize=9, color=INK2)
    b.axvline(4.2, color=INK, linewidth=1.2, linestyle="--")
    b.annotate("face under the coverage bar:\nUNMEASURABLE, not PASS", (max(groups["frozen mouth"]), 2), xytext=(5.4, 1.55),
               fontsize=8, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.8))
    b.text(4.27, 2.45, "gate bar 4.2", fontsize=9, color=INK)
    b.set_yticks(range(len(order)), order)
    b.set_ylim(-0.6, 2.7)
    b.set(xlabel="SyncNet confidence", title="Confidence: real sync vs fakes")
    b.grid(axis="y", visible=False)
    caption(fig, "Data: docs/data/sync-calibration/meter-v1-*.jsonl (2026-09-27; planted controls made by "
                 "rig/sync/make_controls.py). Two same-sentence swaps by another actor (a plausible dub) score 4.5 "
                 "and 6.2 and pass; every different-words swap fails.")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "chart-sync-calibration.png")


# ---------- 2. the shot lab: face size, not framing, decides sync ----------
def shot_lab():
    pts = []
    for r in rows(DATA / "shot-lab" / "results.jsonl"):
        px = r["gate"].get("face_px")
        for ln in r["attribution"]["lines"]:
            sp = ln.get("speaker") or {}
            conf, off = sp.get("conf"), sp.get("offset_ms")
            ok = conf is not None and conf >= 4.2 and off is not None and -125 <= off <= 45
            pts.append((px, conf if conf is not None else r["gate"]["conf"], ok, r["cond"]))   # no speaker: the gate's reading
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    good = [p for p in pts if p[2]]
    bad = [p for p in pts if not p[2]]
    ax.scatter([p[0] for p in good], [p[1] for p in good], s=48, color=BLUE, edgecolor=SURFACE, linewidth=1,
               zorder=3, label=f"line in sync ({len(good)})")
    ax.scatter([p[0] for p in bad], [p[1] for p in bad], s=80, color=RED, marker="X", edgecolor=SURFACE,
               linewidth=1, zorder=4, label=f"line not in sync ({len(bad)})")
    for p in bad:
        ax.annotate(p[3], (p[0], p[1]), xytext=(6, -3), textcoords="offset points", fontsize=8.5, color=INK2)
    ax.axhline(4.2, color=INK, linewidth=1.2, linestyle="--")
    ax.text(480, 4.45, "gate bar 4.2", fontsize=9, ha="right")
    ax.set_xscale("log")
    ax.set_xticks([32, 50, 100, 200, 400], ["32", "50", "100", "200", "400"])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set(xlabel="speaking face height at the line (px, log scale; frame 704x1280 or 1280x704)",
           ylabel="SyncNet confidence for the line",
           title="Shot lab: 35 kinds of speaking shot, 2 seeds each, first takes only")
    ax.legend(loc="lower right", frameon=False)
    caption(fig, "Data: docs/data/shot-lab/results.jsonl (2026-10-03/04, meter v3). One point per spoken line "
                 "(two-person exchanges give two). The clip-level gate passed 63 of 69 clips; scored per line, 66 of "
                 "69 clips were in sync. Every miss had a face under 70 px.")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, "chart-shot-lab.png")


# ---------- 3. films: first-take sync and end-of-film drift ----------
def films():
    rs = list(csv.DictReader(open(DATA / "films" / "summary.csv")))
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.9), gridspec_kw={"width_ratios": [1.25, 1]})
    have = [r for r in rs if r["in_sync_first_take"]]
    names = [r["film"] for r in have]
    y = range(len(have))
    tot = [int(r["dialogue_shots"]) for r in have]
    first = [int(r["in_sync_first_take"]) for r in have]
    final = [int(r["in_sync_final_cut"]) for r in have]
    a.barh(y, tot, color=GRID, height=0.62, label="dialogue shots")
    a.barh(y, final, color="#a9c8ee", height=0.62, label="in sync in the final cut")
    a.barh(y, first, color=BLUE, height=0.62, label="in sync on the first take")
    for i, (t, f, fi) in enumerate(zip(tot, first, final)):
        extra = f", {fi}/{t} final" if fi != f else ""
        a.text(t + 0.3, i, f"{f}/{t} first take{extra}", va="center", fontsize=9, color=INK2)
    a.set_yticks(list(y), names)
    a.invert_yaxis()
    a.set_xlim(0, max(tot) + 9)
    a.set(xlabel="dialogue shots", title="Lines in sync, per film (sync gate)")
    a.grid(axis="y", visible=False)
    a.legend(loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=3, fontsize=8.5, frameon=False)

    dr = [r for r in rs if r["voice_early_at_end_ms"]]
    yd = range(len(dr))
    vals = [int(r["voice_early_at_end_ms"]) for r in dr]
    b.barh(yd, vals, color=[ORANGE if v else AQUA for v in vals], height=0.62)
    for i, v in enumerate(vals):
        b.text(v + 30, i, f"{v} ms" if v else "0 ms (fixed stitch)", va="center", fontsize=9, color=INK2)
    b.set_yticks(list(yd), [r["film"] for r in dr])
    b.invert_yaxis()
    b.set_xlim(0, 2900)
    b.set(xlabel="voice ahead of the lips at film end (ms)", title="Drift as Apple players play it")
    b.grid(axis="y", visible=False)
    caption(fig, "Data: docs/data/films/summary.csv, transcribed from the per-film KPI files beside it. Before "
                 "2026-10-03 the stitch left a ~90 ms audio gap at every cut (docs/data/sync-drift/README.md); "
                 "the iteration-9 film is counted but not shown.")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, "chart-films.png")


# ---------- 4. render wall time ----------
def renders():
    by = defaultdict(lambda: ([], []))
    for r in csv.DictReader(open(DATA / "renders" / "runs.tsv"), delimiter="\t"):
        if r["exit"] != "0":
            continue
        k = f"{r['size']} {r['mode']}"
        by[k][0].append(float(r["clip_seconds"]))
        by[k][1].append(float(r["wall_seconds"]) / 60)
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    style = {"480p fast": (BLUE, "o"), "720p fast": (ORANGE, "s"), "480p quality": (AQUA, "^"),
             "720p quality": (YELLOW, "D")}
    for k, (colour, marker) in style.items():
        xs, ys = by.get(k, ([], []))
        if xs:
            ax.scatter(xs, ys, s=22, color=colour, marker=marker, alpha=0.75, edgecolor="none",
                       label=f"{k} (n={len(xs)})")
    ax.set_yscale("log")
    ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100], ["0.5", "1", "2", "5", "10", "20", "50", "100"])
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set(xlabel="clip length (s)", ylabel="wall time (min, log scale)",
           title="Every LTX-2.5 render on the M5 Max, 2026-09-22 to 2026-10-05")
    ax.legend(loc="upper left", frameon=False)
    caption(fig, "Data: docs/data/renders/runs.tsv (vidgen's own log, prompts removed; exit 0 only). 720p "
                 "includes 1280x704 and 704x1280. Wall time includes model load and audio mux; some runs shared "
                 "the GPU with other work, which is the upper scatter.")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, "chart-render-times.png")


# ---------- 5. the screenplay bench (blind judges) ----------
def screenplay():
    t = open(ROOT / "rig/bench/screenplay/results.md").read()
    block = t.split("## Results", 1)[1].split("\n\n", 2)[1]
    data = []
    for line in block.splitlines()[2:]:
        c = [x.strip() for x in line.strip("|").split("|")]
        o, f = re.match(r"(\d+)", c[5]), re.match(r"(\d+)", c[6])
        if o and f:
            data.append((c[0], c[2], int(o.group(1)), int(f.group(1))))
    data.sort(key=lambda d: d[2] + d[3])
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    y = range(len(data))
    for i, (name, model, o, f) in enumerate(data):
        ax.plot([min(o, f), max(o, f)], [i, i], color=GRID, linewidth=3, zorder=1)
    ax.scatter([d[2] for d in data], list(y), s=70, color=BLUE, zorder=3, edgecolor=SURFACE, label="judge 1 (Claude Opus 5.5)")
    ax.scatter([d[3] for d in data], list(y), s=70, color=ORANGE, marker="s", zorder=3, edgecolor=SURFACE,
               label="judge 2 (Claude Fable 5.1)")
    ax.set_yticks(list(y), [f"{d[0]}  ({d[1]})" for d in data], fontsize=9)
    ax.set_xlim(15, 50)
    ax.set(xlabel="blind score out of 50 (5 criteria x 10)", title="Who writes the funniest usable screenplay?")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", frameon=False)
    caption(fig, "Data: rig/bench/screenplay/results.md, round 1 (2026-10-03), n = 1 run per cell. Same brief, "
                 "screenplays shuffled under letters; Claude Code's own screenplay was in the blind set as a reference. "
                 "Two cells produced no screenplay and are not plotted.")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, "chart-screenplay-bench.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    calibration(); shot_lab(); films(); renders(); screenplay()
