#!/bin/bash
# capture-upstream.sh <out.txt> — stream llama-swap's upstream log (ds4-server's own lines: prefill spans,
# KV cache hits, misses and their reasons, checkpoints, evictions) into a file until killed (2026-09-24).
# llama-swap keeps only about 100 KB of this in memory, which rolls over within the hour, so a film's
# evidence is lost unless this runs from the start. Start it with nohup ... & and kill it at the end.
# The first lines are the buffer's history, so a restart repeats some lines.
exec curl -sN http://127.0.0.1:8090/logs/stream/upstream >> "${1:?usage: capture-upstream.sh <out.txt>}"
