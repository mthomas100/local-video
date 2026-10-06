#!/usr/bin/env python3
"""run-metrics.py [session.jsonl] [--proxy-log FILE] — the numbers a film run is judged by (2026-09-24).

Reads one pi session file (default: the newest session of ~/repos/local-video) and, if given or found,
the llama-swap proxy log (~/.ds4/llama-swap.log) for request durations. Prints: span, requests, output
and thinking volume, compactions with the size each restart re-read, full re-reads (requests with no
cache hit) with their durations, output-cap stops, failed or blocked tool calls, and every render result.
Compare the output with the baseline table in the iteration-3 plan (not published). Read-only; safe during a render."""
import json, os, re, sys, glob
from datetime import datetime, timezone, timedelta

args = sys.argv[1:]
proxy = os.path.expanduser("~/.ds4/llama-swap.log")
if "--proxy-log" in args:
    i = args.index("--proxy-log"); proxy = args[i + 1]; del args[i:i + 2]
sess_dir = os.path.expanduser("~/.pi/agent/sessions/-" + os.path.expanduser("~").replace("/", "-") + "-repos-local-video--")
path = args[0] if args else max(glob.glob(os.path.join(sess_dir, "*.jsonl")), key=os.path.getmtime)
entries = [json.loads(l) for l in open(path) if l.strip()]

def ts(e): return datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
def local(dt): return dt.astimezone().strftime("%H:%M:%S")
msgs = [e for e in entries if e.get("type") == "message"]
asst = [e for e in msgs if e["message"].get("role") == "assistant"]
results = [e for e in msgs if e["message"].get("role") == "toolResult"]
def usage(e): return e["message"].get("usage") or {}
def prompt_tokens(e): u = usage(e); return (u.get("input") or 0) + (u.get("cacheRead") or 0) + (u.get("cacheWrite") or 0)
def text(e): return " ".join(c.get("text", "") for c in e["message"].get("content", []) if isinstance(c, dict))
def thinking(e): return sum(len(c.get("thinking", "")) for c in e["message"].get("content", []) if c.get("type") == "thinking")

# Request durations from the proxy log, keyed by local completion time (the log has no year or zone).
durations = {}
if os.path.exists(proxy):
    pat = re.compile(r'^(\w{3} +\d+ \d\d:\d\d:\d\d) \[INFO\] Request .*POST /v1/chat/completions.*" ([0-9hms.µ]+)$')
    for line in open(proxy, errors="replace"):
        m = pat.match(line.strip())
        if m: durations.setdefault(m.group(1)[-8:], []).append(m.group(2))
def secs(d):
    t = 0.0
    for v, u in re.findall(r"([0-9.]+)(h|ms|µs|m|s)", d): t += float(v) * {"h": 3600, "m": 60, "s": 1, "ms": 1e-3, "µs": 1e-6}[u]
    return t
def duration_near(dt):
    for off in (0, 1, -1, 2, -2):
        k = (dt + timedelta(seconds=off)).astimezone().strftime("%H:%M:%S")
        if k in durations: return secs(durations[k][0])
    return None

first, last = ts(msgs[0]), ts(msgs[-1])
print(f"session   {path}")
print(f"span      {local(first)} -> {local(last)}  ({(last - first).total_seconds() / 60:.0f} min)")
print(f"requests  {len(asst)} model replies; output {sum(usage(e).get('output') or 0 for e in asst):,} tokens; "
      f"thinking {sum(thinking(e) for e in asst):,} chars; largest context {max((usage(e).get('totalTokens') or 0) for e in asst):,} tokens")
stops = [e for e in asst if e["message"].get("stopReason") in ("length", "error", "aborted")]
print(f"bad stops {len(stops)}" + "".join(f"\n          {local(ts(e))} {e['message']['stopReason']} out={usage(e).get('output')}" for e in stops))

print("compactions (tokens before -> the next request's prompt, which it re-reads):")
for c in (e for e in entries if e.get("type") == "compaction"):
    nxt = next((a for a in asst if ts(a) > ts(c)), None)
    after = f"{prompt_tokens(nxt):,}" if nxt else "no request after it"
    print(f"          {local(ts(c))} {c.get('tokensBefore'):,} -> {after}  summary {len(c.get('summary', '')):,} chars")

rr = [e for e in asst if (usage(e).get("cacheRead") or 0) == 0]
total = 0.0
print(f"full re-reads {len(rr)} (no cache hit; the first request of a session is expected):")
for e in rr:
    d = duration_near(ts(e)); total += d or 0
    print(f"          {local(ts(e))} prompt {prompt_tokens(e):,} tokens, out {usage(e).get('output') or 0}"
          + (f", request {d / 60:.1f} min" if d else ""))
if total: print(f"          total request time of those: {total / 60:.1f} min (includes their output)")

bad = [e for e in results if e["message"].get("isError")]
print(f"failed or blocked tool calls {len(bad)}" + "".join(
    f"\n          {local(ts(e))} {e['message'].get('toolName')}: {text(e)[:90]}" for e in bad))
print("renders:")
for e in results:
    if re.search(r"render_and_wait|redo_scenes", e["message"].get("toolName", "")):
        print(f"          {local(ts(e))} {e['message']['toolName']}: {text(e).splitlines()[0][:110]}")
