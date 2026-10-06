# rig/audit — watching a film run and judging it with numbers (2026-09-24)

Written while auditing the `nyc-2000-slavic-neon` run live; the findings went into a private post-mortem. Everything here is read-only and safe during a render.

| tool | use |
|---|---|
| `run-metrics.py [session.jsonl]` | after (or during) a run: span, replies, output and thinking volume, compactions and restart sizes, full re-reads with their request time, output-cap stops, failed or blocked tool calls, render results. Default: the newest local-video session. This is the comparison against the baseline in the iteration-3 plan (not published). |
| `watch-pi.sh [max-seconds]` | blocks until a compaction, a bad stop, a render/review result or a user message appears in the live session, prints it and exits; `MODE=next-assistant` also exits on any model reply. Run it with `run_in_background` from Claude Code and restart it after each event. |
| `last-replies.py [n] [session.jsonl]` | the text and tool calls of the director's last n replies: its interview question, verdicts, redo plan, final report. |
| `sample-mem.sh <out.csv> [max-seconds]` | 5 s samples of phase (render, llm, idle), memory and GPU load. `nohup … &` at the start, kill at the end. |
| `session-timeline.py [session.jsonl]` | a metadata-only copy of a pi session (times, roles, usage, thinking and text sizes, tool calls, result heads, images), the format kept as run evidence. |
| `capture-upstream.sh <out.txt>` | streams ds4-server's own log lines (prefill spans, cache hits and misses with their reasons, checkpoints, evictions) to a file. llama-swap keeps only about 100 KB, so start it before the film. |

Where the raw material lives: the pi session under `~/.pi/agent/sessions/--Users-<you>-repos-local-video--/`,
the proxy log `~/.ds4/llama-swap.log` (request durations, loads, unloads), and the render logs in `logs/`.
Evidence worth keeping goes into the design notes (kept in a private wiki), not into this repo.
