# Measured data behind the README charts

Copied from the rig's iteration folders on 2026-10-05, with home paths shortened to `~`. Nothing here is
re-measured or edited; `docs/charts/make_charts.py` reads these files directly.

| folder | what | made by |
|---|---|---|
| `sync-calibration/meter-v1-controls.jsonl` | the sync meter on planted controls cut from five of our own LTX clips: shifts -400..+400 ms, frozen mouth, hidden face, swapped voice (2026-09-27) | `rig/sync/make_controls.py`, `rig/sync/syncmeter.py` |
| `sync-calibration/meter-v1-ravdess.jsonl` | the same controls on six RAVDESS actor recordings (measurements only; the dataset is not redistributed) | same |
| `sync-calibration/zero-reference.jsonl` | the meter on SyncNet's own published example clip, through every codec and frame-rate path the rig uses | same |
| `sync-calibration/floor*.jsonl`, `controls.jsonl` | the shrink test: in-sync mouths scaled down to 1.4-8% of the frame with planted shifts, and frozen/swapped controls at small sizes (2026-10-03) | the shot lab's `floor_measure.py`, `scale_test2.py`, `controls_measure.py` (not published) |
| `sync-calibration/warm-wide-min0.jsonl` | Warm's UNMEASURABLE wide takes re-read with the face floor removed | same |
| `sync-calibration/mouthing.jsonl`, `delivery-ravdess.jsonl` | silent articulation and the delivery meter on known answers | `rig/sync/mouthing.py`, `rig/sync/delivery.py` |
| `shot-lab/` | the shot lab: 69 first takes across 35 conditions, per-clip gate rows (`results.jsonl`), the per-condition summary, the generator and the project files | `make_lab.py`, `rig/sync/gate.py` |
| `sync-drift/` | the stitch drift: old film, player view and fixed stitch, three shots of Warm | `rig/sync/drift.py`, `rig/sync/syncmeter.py` |
| `films/` | per-film gate rows (`*.jsonl`), each iteration's KPI page, the sync reports, and `summary.csv` (transcribed from those pages) | `rig/sync/backmeasure.py`, the iteration notes |
| `renders/runs.tsv` | every `vidgen` render 2026-09-22 to 2026-10-05: time, pack, mode, size, clip seconds, wall seconds, exit code (prompts and file names removed) | `bin/vidgen` |

Sign convention everywhere: a positive offset means the voice is early (before the mouth).
The scripts in `shot-lab/` are an archive of the lab as it ran; they assume the rig at `~/repos/local-video` and the
iteration folder layout, and some `evidence/` files they mention were not published.
