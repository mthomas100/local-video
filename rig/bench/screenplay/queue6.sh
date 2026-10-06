#!/bin/zsh
# queue6.sh — held-out validation of screenplay skill v3 (brief2: a nature-doc parody), 2 runs per cell.
E=${0:A:h}; cd $E; echo $$ > runs/queue.pid
step() { grep -q "rc=0" runs/$1/meta.txt 2>/dev/null && [ -s runs/$1/screenplay.md ] && return
  if [ -e runs/PAUSE ]; then echo "paused $(date +%H:%M)"; while [ -e runs/PAUSE ]; do sleep 15; done; fi; "${@:2}"; }
export BRIEF=brief2.txt
for i in 1 2; do
  step b2-qwen38-P2g-$i ./run.sh b2-qwen38-P2g-$i prompts/P2g-craft-brief2.txt qwen38 medium
  step b2-qwen38-skill-$i ./run-skill2.sh b2-qwen38-skill-$i qwen38 medium
done
for i in 1 2; do
  step b2-q4-P2g-$i ./run.sh b2-q4-P2g-$i prompts/P2g-craft-brief2.txt vision-q4-400k medium
  step b2-q4-skill-$i ./run-skill2.sh b2-q4-skill-$i vision-q4-400k medium
done
curl -s 127.0.0.1:8090/unload; echo "QUEUE DONE $(date +%H:%M)"
