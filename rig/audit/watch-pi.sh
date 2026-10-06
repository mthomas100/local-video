#!/bin/bash
# watch-pi.sh [max-seconds] — block until something notable happens in the live pi film session, print it,
# exit 0 (2026-09-24). Notable: a compaction, a reply that stopped on the output cap, an error or an abort,
# a render_and_wait / redo_scenes / review_scenes result, a user message, a failed tool call, and (since
# 2026-09-26) TURN END: a reply that ends the model's turn, i.e. the director now waits for the human (an
# interview question, the look pick, the final report). With MODE=next-assistant, any model reply counts.
# SESSION=<file.jsonl> overrides the default, the newest session of ~/repos/local-video: pass it explicitly
# once pi has written its first message, because a watcher started before that attaches to the previous
# session (it did on 2026-09-25). Run it in the background from Claude Code (run_in_background) so each event
# wakes the auditor; restart it after every event. Read-only; safe during a render.
SESSION=${SESSION:-$(ls -t ~/.pi/agent/sessions/-${HOME//\//-}-repos-local-video--/*.jsonl | head -1)}
echo "watching $SESSION" >&2
seen=$(wc -l < "$SESSION")
deadline=$(( $(date +%s) + ${1:-3600} ))
while :; do
  n=$(wc -l < "$SESSION")
  if [ "$n" -gt "$seen" ]; then
    ev=$(tail -n +$((seen+1)) "$SESSION" | jq -rR 'fromjson? |
      if .type=="compaction" then "COMPACTION tokensBefore=\(.tokensBefore) at \(.timestamp)"
      elif .type=="message" and .message.role=="assistant" and ((.message.stopReason // "")|test("length|error|aborted")) then "STOP=\(.message.stopReason) at \(.timestamp) out=\(.message.usage.output) \(.message.errorMessage // "")"
      elif .type=="message" and .message.role=="assistant" and .message.stopReason=="stop" then "TURN END at \(.timestamp) out=\(.message.usage.output) ctx=\(.message.usage.totalTokens): the model waits for the human"
      elif .type=="message" and .message.role=="toolResult" and ((.message.toolName // "")|test("render_and_wait|redo_scenes|review_scenes")) then "RESULT \(.message.toolName) at \(.timestamp): \([.message.content[]? | .text? // ""] | join(" ") | .[0:400])"
      elif .type=="message" and .message.role=="toolResult" and .message.isError then "TOOL ERROR \(.message.toolName) at \(.timestamp): \([.message.content[]? | .text? // ""] | join(" ") | .[0:300])"
      elif .type=="message" and .message.role=="user" then "USER message at \(.timestamp)"
      elif env.MODE=="next-assistant" and .type=="message" and .message.role=="assistant" then "ASSISTANT at \(.timestamp) out=\(.message.usage.output) ctx=\(.message.usage.totalTokens) calls=\([.message.content[] | select(.type=="toolCall") | .name] | join(","))"
      else empty end')
    seen=$n
    if [ -n "$ev" ]; then echo "EVENT $(date +%H:%M:%S) (session lines=$n):"; echo "$ev"; exit 0; fi
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then echo "HEARTBEAT $(date +%H:%M:%S): nothing notable; session lines=$n"; exit 0; fi
  sleep 15
done
