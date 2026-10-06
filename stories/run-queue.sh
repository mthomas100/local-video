#!/bin/zsh
# run-queue.sh <project-file>... — run projects back to back, unattended, skipping finished ones
# and continuing past a failure (2026-09-23). Log: logs/queue.log. Kill: pkill -f run-queue.sh
Q=~/repos/local-video/logs/queue.log
# One GPU lock for the Mac (2026-10-04, ~/repos/local-rig/docs/hold.md): the whole queue runs under one hold, so no
# model call reloads the LLM between scenes or films; started by render_and_wait, it joins that tool's hold (HOLD_ID).
if [ -z "${HOLD_ID:-}" ] && command -v hold >/dev/null; then exec hold run --kind render --reason "run-queue ${${1:t}:r}" -- zsh $0 "$@"; fi
for p in "$@"; do
  name=$(grep -m1 '^NAME=' $p | cut -d= -f2 | cut -d';' -f1)   # "NAME=x; SIZE=..." on one line
  if [ -s ~/Videos/vidgen/$name/$name.mp4 ]; then echo "$(date +%H:%M) $name already done" >> $Q; continue; fi
  echo "$(date +%H:%M) START $name" >> $Q
  zsh ~/repos/local-video/stories/story.sh $p >> $Q 2>&1; rc=$?
  case $rc in 0) echo "$(date +%H:%M) OK $name" >> $Q;; 3) echo "$(date +%H:%M) PAUSED $name" >> $Q;; 4) echo "$(date +%H:%M) SYNCGATE $name" >> $Q;; *) echo "$(date +%H:%M) FAILED $name" >> $Q;; esac
done
echo "$(date +%H:%M) QUEUE FINISHED" >> $Q
