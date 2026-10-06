#!/bin/zsh
# run-skill.sh NAME MODEL THINKING — validate the screenplay skill: pi loads skills/screenplay as a user would
# (/skill:screenplay), works from the repo root with read/write/edit/bash, and writes to runs/NAME/screenplay.md.
set -u
E=${0:A:h}; N=$1; M=$2; T=$3; R=$E/runs/$N; mkdir -p $R/session; REPO=${E:h:h:h}
out=$R/screenplay.md; rm -f $out
msg="/skill:screenplay $(cat $E/brief.txt) Write the screenplay to $out and your notes to $R/notes.md (instead of stories/screenplays/). Work alone: don't ask me anything."
sys="You are a screenwriter and director for short AI-generated films on a local film rig. Work alone: never ask the user questions."
t0=$(date +%s)
cd $REPO && pi -p --model local/$M --thinking $T --system-prompt "$sys" --tools read,write,edit,bash -ne -nc -np --no-themes \
  --skill $REPO/skills/screenplay --session-dir $R/session "$msg" > $R/stdout.txt 2> $R/stderr.txt; rc=$?
t1=$(date +%s)
print "name=$N prompt=skill model=$M thinking=$T rc=$rc seconds=$((t1-t0)) words=$( [ -s $out ] && wc -w < $out || echo 0)" | tee $R/meta.txt
