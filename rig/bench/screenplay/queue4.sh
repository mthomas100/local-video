#!/bin/zsh
# queue4.sh — the rest of the screenplay eval. Before each run it waits while runs/PAUSE exists (touch it to give
# another session a GPU gap between runs; unload by hand first: the queue never unloads while paused, since another
# session's llama-swap model may be the one loaded). Skips runs already done.
E=${0:A:h}; cd $E; echo $$ > runs/queue.pid
step() {
  grep -q "rc=0" runs/$1/meta.txt 2>/dev/null && [ -s runs/$1/screenplay.md ] && return
  if [ -e runs/PAUSE ]; then echo "paused $(date +%H:%M)"; while [ -e runs/PAUSE ]; do sleep 15; done; fi
  ./run.sh "$@"
}
step q2-P2-med prompts/P2-craft.txt vision-500k medium
step qwen38-P2 prompts/P2-craft.txt qwen38 medium
# Think Max with a 64K reply cap (a private pi config; the shared one caps replies at 16,384, all spent on thinking)
export PI_CODING_AGENT_DIR=$E/agent-bigout
step q4-P2-max64k prompts/P2-craft.txt vision-q4-400k max
unset PI_CODING_AGENT_DIR
curl -s 127.0.0.1:8090/unload; echo "QUEUE DONE $(date +%H:%M)"
