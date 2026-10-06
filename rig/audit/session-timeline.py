#!/usr/bin/env python3
"""session-timeline.py [session.jsonl] > timeline.jsonl — a metadata-only copy of a pi session (2026-09-24).

One JSON line per entry: time, type, id, and for messages the role, stop reason, token usage, the sizes of
thinking and text, the tool calls (name and argument size) and, for tool results, the tool, the text size,
the number of images and the first line. No message content beyond that first line, so it can be kept
as run evidence without keeping the transcript. Default: the newest local-video session."""
import glob, json, os, sys

sess_dir = os.path.expanduser("~/.pi/agent/sessions/-" + os.path.expanduser("~").replace("/", "-") + "-repos-local-video--")
path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(os.path.join(sess_dir, "*.jsonl")), key=os.path.getmtime)
for line in open(path):
    if not line.strip():
        continue
    e = json.loads(line)
    out = {"t": e.get("timestamp"), "type": e.get("type"), "id": e.get("id")}
    t = e.get("type")
    if t == "model_change":
        out["model"] = e.get("modelId") or e.get("model")
    elif t == "thinking_level_change":
        out["thinkingLevel"] = e.get("thinkingLevel")
    elif t == "compaction":
        out.update(tokensBefore=e.get("tokensBefore"), summary_chars=len(e.get("summary") or ""),
                   retained=len(e.get("retainedTail") or []), usage=(e.get("details") or {}).get("usage") if isinstance(e.get("details"), dict) else None)
    elif t == "custom":
        out.update(customType=e.get("customType"), data=e.get("data"))
    elif t == "message":
        m = e["message"]; role = m.get("role"); out["role"] = role
        content = m.get("content")
        parts = content if isinstance(content, list) else [{"type": "text", "text": content or ""}]
        text_chars = sum(len(p.get("text", "")) for p in parts if isinstance(p, dict) and p.get("type") == "text")
        if role == "assistant":
            u = m.get("usage") or {}
            out.update(stop=m.get("stopReason"), usage={k: u.get(k) for k in ("input", "output", "cacheRead", "cacheWrite")} | {"total": u.get("totalTokens")},
                       thinking_chars=sum(len(p.get("thinking", "")) for p in parts if p.get("type") == "thinking"), text_chars=text_chars)
            calls = [{"name": p.get("name"), "arg_chars": len(json.dumps(p.get("arguments", {})))} for p in parts if p.get("type") == "toolCall"]
            if calls: out["calls"] = calls
            if m.get("errorMessage"): out["error"] = str(m["errorMessage"])[:200]
        elif role == "toolResult":
            first = next((p.get("text", "") for p in parts if p.get("type") == "text"), "")
            out.update(tool=m.get("toolName"), text_chars=text_chars, images=sum(1 for p in parts if p.get("type") == "image"),
                       is_error=bool(m.get("isError")), result_head=first.split("\n")[0][:160])
        else:
            out["text_chars"] = text_chars
    print(json.dumps(out, ensure_ascii=False))
