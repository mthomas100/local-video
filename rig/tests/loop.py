#!/usr/bin/env python3
"""loop.py — the full alternation loop from a NORMAL pi session, headless (2026-09-23): extension discovery on
(every extension in ~/.pi/agent/extensions, film-rig among them), a persisted session, a vision model, and only
/film typed in. The model must itself call render_and_wait on the two-scene smoke project, be unloaded, wait, be
reloaded on its next reply and review the sheet. Prints the key events and samples llama-swap during the render.
Since 2026-09-24 the render result is text only and the model must call review_scenes for the sheet; a follow-up
prompt makes one more request, in which the answered sheet has been replaced by a note (check the ds4 log for a
cache hit there: rig/audit/capture-upstream.sh). Needs an idle GPU and no ~/Videos/vidgen/rig-smoke folder.
Leaves the model loaded: unload it afterwards."""
import json, subprocess, sys, time, threading, queue, os, urllib.request
model = sys.argv[1] if len(sys.argv) > 1 else "local/vision"
repo = os.path.expanduser("~/repos/local-video")
cmd = ["pi", "--mode", "rpc", "--offline", "--model", model, "--name", "film-rig loop test"]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, cwd=repo)
q: "queue.Queue[str | None]" = queue.Queue()
threading.Thread(target=lambda: ([q.put(l.rstrip("\n")) for l in p.stdout], q.put(None)), daemon=True).start()
def send(o): p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
def swap_running():
    try: return [m["model"] for m in json.load(urllib.request.urlopen("http://127.0.0.1:8090/running", timeout=3)).get("running", [])]
    except Exception: return ["unreachable"]
ts = lambda: time.strftime("%H:%M:%S")
samples = []; tool_seen = False; ok = True
def check(c, what):
    global ok; ok = ok and c; print(("ok: " if c else "FAIL: ") + what)
def drain(seconds, stop=None, quiet=False):
    global tool_seen
    out, end, last_sample = [], time.time() + seconds, 0
    while time.time() < end:
        try: line = q.get(timeout=0.5)
        except queue.Empty:
            if tool_seen and time.time() - last_sample > 20:
                last_sample = time.time(); s = swap_running(); samples.append(s); print(ts(), "llama-swap running during the tool:", s)
            continue
        if line is None: break
        try: ev = json.loads(line)
        except Exception: continue
        out.append(ev); t = ev.get("type")
        if t == "extension_ui_request" and ev.get("method") == "notify": print(ts(), "notify:", ev.get("message", "")[:160].replace("\n", " "))
        elif t == "tool_execution_start": tool_seen = tool_seen or ev.get("toolName") == "render_and_wait"; print(ts(), "tool start:", ev.get("toolName"), json.dumps(ev.get("args", ev.get("input", {})))[:160])
        elif t == "tool_execution_end": print(ts(), "tool end:", ev.get("toolName"), "error" if ev.get("isError") else "ok")
        elif t == "message_end" and ev.get("message", {}).get("role") == "assistant":
            txt = " ".join(c.get("text", "") for c in ev["message"].get("content", []) if c.get("type") == "text")
            if txt.strip(): print(ts(), "assistant:", txt[:700].replace("\n", " "))
        elif t == "agent_end": print(ts(), "agent_end")
        if stop and stop(ev): break
    return out
time.sleep(2); start = drain(4)
check(any("film-rig: mode=" in e.get("message", "") for e in start if e.get("type") == "extension_ui_request"), "film-rig auto-loaded in a normal session")
brief = ("/film This is a smoke test of the rig, not a real film. Do not write a new project file. Use the existing project "
         "stories/projects/00-rig-smoke.txt exactly as it is (2 scenes of 5 s at 480p, already interviewed: fast mode, photoreal). "
         "Skip the interview. Call render_and_wait on it now with sheet \"1 2\", then call review_scenes as its result says, "
         "give a one-line asked/shows verdict per scene, then stop. Do not redo anything.")
send({"id": "1", "type": "prompt", "message": brief})
evs = drain(900, lambda e: e.get("type") == "agent_end")
print("--- after the turn: llama-swap running:", swap_running())
check(any(e.get("type") == "tool_execution_start" and e.get("toolName") == "render_and_wait" for e in evs), "the model itself called render_and_wait")
check(any(s == [] for s in samples), "llama-swap had nothing loaded while the tool ran (model unloaded)")
last = [e for e in evs if e.get("type") == "message_end" and e.get("message", {}).get("role") == "assistant"]
txt = " ".join(c.get("text", "") for e in last[-1:] for c in e["message"].get("content", []) if c.get("type") == "text") if last else ""
check(any(w in txt.lower() for w in ("scene 1", "scene 2", "clip 1", "clip 2", "row 1", "row 2", "asked", "shows")), "the model woke up and reviewed the sheet")
check(swap_running() == ["vision"] or model.split("/")[-1] in swap_running(), "the model is loaded again after the wake")
ends = [e for e in evs if e.get("type") == "tool_execution_end"]
has_img = lambda e: any(c.get("type") == "image" for c in (e.get("result") or {}).get("content", []))
check(any(e.get("toolName") == "render_and_wait" and not has_img(e) for e in ends), "render_and_wait returned text only (no image in the wake request)")
check(any(e.get("toolName") == "review_scenes" and has_img(e) for e in ends), "the model called review_scenes and got the sheet as an image")
send({"id": "2", "type": "prompt", "message": "Thanks. Reply with only the word DONE."})
evs2 = drain(300, lambda e: e.get("type") == "agent_end")
last2 = [e for e in evs2 if e.get("type") == "message_end" and e.get("message", {}).get("role") == "assistant"]
check(bool(last2), "a follow-up request after the review (its context carries the sheet as a one-line note)")
send({"id": "9", "type": "prompt", "message": "/film off"}); drain(10, lambda e: e.get("type") == "response" and e.get("id") == "9")
p.stdin.close()
try: p.wait(timeout=10)
except Exception: p.kill()
print("ALL OK" if ok else "FAILED"); sys.exit(0 if ok else 1)
