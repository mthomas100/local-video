#!/bin/zsh
# queue2.sh — the rest of the screenplay eval. Before each run it waits while runs/PAUSE exists (touch it to give
# another session a GPU gap between runs; the model is unloaded while paused). Skips runs already done.
E=${0:A:h}; cd $E
step() {
  [ -s runs/$1/meta.txt ] && return
  if [ -e runs/PAUSE ]; then curl -s 127.0.0.1:8090/unload >/dev/null; echo "paused $(date +%H:%M)"; while [ -e runs/PAUSE ]; do sleep 15; done; fi
  ./run.sh "$@"
}
step q4-P3-med prompts/P3-revise.txt vision-q4-400k medium
step q4-P2-off prompts/P2-craft.txt vision-q4-400k off
step q4-P2-max prompts/P2-craft.txt vision-q4-400k max
step q2-P2-med prompts/P2-craft.txt vision-500k medium
step qwen38-P2 prompts/P2-craft.txt qwen38 medium
curl -s 127.0.0.1:8090/unload; echo "QUEUE DONE $(date +%H:%M)"
