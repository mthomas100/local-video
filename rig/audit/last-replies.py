#!/usr/bin/env python3
"""last-replies.py [n] [session.jsonl] — the text and tool calls of the director's last n replies (2026-09-26).

For the auditor during a run: read what the local model just said or decided (an interview question, its
asked/shows verdicts, a redo plan, the final report) without attaching to its tmux pane. Default: the last reply
of the newest local-video pi session. Read-only; safe during a render."""
import glob, json, os, sys

args = sys.argv[1:]
n = int(args[0]) if args and args[0].isdigit() else 1
paths = [a for a in args if a.endswith(".jsonl")]
sess_dir = os.path.expanduser("~/.pi/agent/sessions/-" + os.path.expanduser("~").replace("/", "-") + "-repos-local-video--")
path = paths[0] if paths else max(glob.glob(os.path.join(sess_dir, "*.jsonl")), key=os.path.getmtime)
out = []
for line in open(path):
    e = json.loads(line)
    if e.get("type") != "message" or e["message"].get("role") != "assistant":
        continue
    m = e["message"]
    text = " ".join(c.get("text", "") for c in m.get("content", []) if c.get("type") == "text")
    calls = [f"{c.get('name')}: {json.dumps(c.get('arguments', {}), ensure_ascii=False)[:400]}" for c in m.get("content", []) if c.get("type") == "toolCall"]
    u = m.get("usage") or {}
    out.append(f"--- {e['timestamp']} stop={m.get('stopReason')} out={u.get('output')} ctx={u.get('totalTokens')}\n{text}"
               + ("\ncalls: " + "\n       ".join(calls) if calls else ""))
print(path)
print("\n".join(out[-n:]))
