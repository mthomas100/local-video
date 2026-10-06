#!/usr/bin/env python3
"""rpc.py — drive a REAL headless pi session (pi --mode rpc) and type the /film commands into it (2026-09-23).
Loads the model given by --model (default local/vision-500k via llama-swap; needs an idle GPU), then:
/film status -> preflight notify; /film <brief> -> director mode on, brief sent, the model answers as the
director (its interview question proves the director prompt was appended); /film off. Exit 0 on success.
Leaves the model loaded in llama-swap: `curl 127.0.0.1:8090/unload` afterwards if nothing else needs it."""
import json, subprocess, sys, time, threading, queue, os
model = sys.argv[1] if len(sys.argv) > 1 else "local/vision-500k"
repo = os.path.expanduser("~/repos/local-video")
cmd = ["pi", "--mode", "rpc", "--offline", "--no-extensions", "-e", f"{repo}/rig/film-rig.ts", "--model", model, "--no-session"]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, cwd=repo)
q: "queue.Queue[str | None]" = queue.Queue()
threading.Thread(target=lambda: ([q.put(l.rstrip("\n")) for l in p.stdout], q.put(None)), daemon=True).start()
def send(o): p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
def drain(seconds, stop=None):
    out, end = [], time.time() + seconds
    while time.time() < end:
        try: line = q.get(timeout=0.5)
        except queue.Empty: continue
        if line is None: break
        try: ev = json.loads(line)
        except Exception: continue
        out.append(ev)
        if stop and stop(ev): break
    return out
def notifies(evs): return [e.get("message", "") for e in evs if e.get("type") == "extension_ui_request" and e.get("method") == "notify"]
def assistant(evs):
    for e in evs:
        if e.get("type") == "message_end" and e.get("message", {}).get("role") == "assistant":
            return " ".join(c.get("text", "") for c in e["message"].get("content", []) if c.get("type") == "text")
    return ""
ok = True
def check(cond, what):
    global ok; ok = ok and cond; print(("ok: " if cond else "FAIL: ") + what)
time.sleep(2); start = drain(3)
check(any("film-rig: mode=" in n for n in notifies(start)), "session_start notify")
send({"id": "1", "type": "prompt", "message": "/film status"})
evs = drain(20, lambda e: e.get("type") == "response" and e.get("id") == "1")
check(any('"lifecycle"' in n for n in notifies(evs)), "/film status shows the preflight")
send({"id": "2", "type": "prompt", "message": "/film A one-scene test: a red kite over a grey beach. Answer only the interview in one short line; do not write any file yet."})
evs = drain(300, lambda e: e.get("type") == "agent_end")
check(any("director mode ON" in n for n in notifies(evs)), "/film <brief> turns director mode on")
a = assistant(evs); print("  assistant:", a[:300].replace("\n", " "))
check(bool(a) and any(w in a.lower() for w in ("480p", "720p", "scenes", "fast", "quality")), "the model answers as the director (interview)")
send({"id": "3", "type": "prompt", "message": "/film off"})
evs = drain(10, lambda e: e.get("type") == "response" and e.get("id") == "3")
check(any("director mode off" in n for n in notifies(evs)), "/film off")
p.stdin.close()
try: p.wait(timeout=10)
except Exception: p.kill()
print("ALL OK" if ok else "FAILED"); sys.exit(0 if ok else 1)
