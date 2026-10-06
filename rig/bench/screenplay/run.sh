#!/bin/zsh
# run.sh NAME PROMPT MODEL THINKING — one screenplay-writing run of pi (2026-10-03 screenplay eval).
# pi gets the prompt with OUT_PATH filled in, a fixed neutral system prompt, only read/write/edit tools, no skills,
# extensions or context files. Output: runs/NAME/screenplay.md, runs/NAME/session/*.jsonl, runs/NAME/meta.txt.
set -u
E=${0:A:h}; N=$1; P=$2; M=$3; T=$4; R=$E/runs/$N; mkdir -p $R/session
out=$R/screenplay.md; rm -f $out
msg=$(sed "s|OUT_PATH|$out|g" $P)
sys="You are a screenwriter and director for short AI-generated films on a local film rig. You write files with the write and edit tools. Work alone: never ask the user questions."
t0=$(date +%s)
cd $R && pi -p --model local/$M --thinking $T --system-prompt "$sys" --tools read,write,edit -ne -ns -nc -np --no-themes \
  --session-dir $R/session "$msg" > $R/stdout.txt 2> $R/stderr.txt; rc=$?
t1=$(date +%s)
print "name=$N prompt=${P:t} model=$M thinking=$T rc=$rc seconds=$((t1-t0)) words=$( [ -s $out ] && wc -w < $out || echo 0)" | tee $R/meta.txt
