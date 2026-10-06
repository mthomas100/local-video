#!/usr/bin/env python3
"""ds4-imgcache-check.py — does ds4-server reuse its cache for an image-bearing request? (2026-09-26)

Drives ONE standalone ds4-server the way pi drives the film director through llama-swap: streaming chat
completions with tools, the model's reasoning sent back as `reasoning_content`, tool results as `tool`
messages, and images as a trailing `user` message ("Attached image(s) from tool result:", pi-ai's
openai-completions conversion). Between turn 1 and turn 2 the server is stopped gracefully and restarted,
as llama-swap unloads the director for every render, so turn 2 restores from the KV disk cache.

  turn 1  system (the director prompt) + user task          -> the model calls read_file
  -- graceful stop (shutdown checkpoint) and restart --
  turn 2  + the call and its tool result (text)              -> the model calls review_sheet
  turn 3  + the call, its tool result and the IMAGE (--scenario image), or the same without the image
          (--scenario text)                                  -> the review: THE REQUEST UNDER TEST
  turn 4  + the reply and a text follow-up (the image replaced by a note, as the rig's context hook does)

It prints each request's time and ds4's own log lines for it (prefill span `ctx=cached..prompt`, cache hits
and misses), and writes everything to --out as JSON. Run it once per binary with a fresh --kv-dir each time,
nothing else on the GPU, llama-swap unloaded. The server's log holds only this script's synthetic prompts.

  ds4-imgcache-check.py --binary ~/repos/ds4/ds4-server --chdir ~/repos/ds4 --scenario image --kv-dir DIR --out F
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parents[2]
GGUF = HOME / "repos/ds4/gguf"
MODEL = GGUF / "DeepSeek-V4-Flash-Vision-Exp-Layers37-42Q4KExperts-OtherExpertLayersIQ2XXSGateUp-Q2KDown-AProjQ8-SExpQ8-OutQ8.gguf"
VISION = GGUF / "DeepSeek-V4-Flash-Vision-Encoder.gguf"

TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file of the film project.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "review_sheet", "description": "Show the contact sheet of rendered clips (an image).",
                                      "parameters": {"type": "object", "properties": {"scenes": {"type": "string"}}, "required": ["scenes"]}}},
]
TASK = ("We are checking the first rendered shot of a short film. Step 1: call read_file with path "
        "\"stories/projects/brief.txt\". Step 2: after you have read it, call review_sheet with scenes \"2\". "
        "Step 3: when you see the sheet, write one line: \"clip 2: asked ... / shows ... / keep or redo\". "
        "Use exactly one tool call per reply.")
BRIEF = ("Shot 2: On the Golden Gate Bridge, a huge rust-red suspension bridge with two tall Art Deco towers, at "
         "night in thick bay fog, a slow aerial drone shot glides low over the empty deck. A real giant pumpkin taller "
         "than a person sits in the middle of the roadway, its carved face glowing orange. Rain, fog horns.")


def start(a, log) -> subprocess.Popen:
    cmd = [str(a.binary), "--chdir", str(a.chdir), "-m", str(MODEL), "--ctx", "100000",
           "--kv-disk-dir", str(a.kv_dir), "--kv-disk-space-mb", "65536", "--vision", str(VISION), "--port", str(a.port)]
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < 300:
        if p.poll() is not None:
            sys.exit(f"ds4-server exited with {p.returncode} while starting")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{a.port}/v1/models", timeout=2).read()
            print(f"server up in {time.time() - t0:.1f} s", flush=True)
            return p
        except Exception:
            time.sleep(1)
    stop(p)
    sys.exit("ds4-server did not come up in 300 s")


def stop(p: subprocess.Popen) -> None:
    """Graceful: SIGTERM and wait (ds4 persists its resident KV cache on the way out). Never SIGKILL."""
    if p.poll() is None:
        p.send_signal(signal.SIGTERM)
        try:
            p.wait(timeout=240)
        except subprocess.TimeoutExpired:
            print("WARNING: ds4-server still running 240 s after SIGTERM; left running, not killed", flush=True)


def chat(port: int, messages: list, tools: list, max_tokens: int) -> dict:
    body = {"model": "deepseek-v4-flash", "messages": messages, "tools": tools, "stream": True, "max_tokens": max_tokens,
            "reasoning_effort": "medium", "temperature": 0, "seed": 7}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    content, reasoning, calls, finish, usage = "", "", {}, None, {}
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            j = json.loads(data)
            usage = j.get("usage") or usage
            for ch in j.get("choices", []):
                d = ch.get("delta", {})
                content += d.get("content") or ""
                reasoning += d.get("reasoning_content") or ""
                for tc in d.get("tool_calls") or []:
                    c = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                    c["id"] = tc.get("id") or c["id"]
                    f = tc.get("function") or {}
                    c["name"] += f.get("name") or ""
                    c["arguments"] += f.get("arguments") or ""
                finish = ch.get("finish_reason") or finish
    return {"content": content, "reasoning": reasoning, "calls": [calls[k] for k in sorted(calls)], "finish": finish,
            "usage": usage, "seconds": round(time.time() - t0, 2)}


# What llama-swap (sendLoadingState: true) streams as reasoning_content while it loads a model: pi stores it as the
# model's thinking and replays it (the halloween run, 2026-09-25: the first reply after each of the 4 reloads).
BANNER = ("━━━━━\nllama-swap loading model: vision-q4\n\nSorry, the inference you have reached is not in service "
          "..........\nTeaching the model manners ............\nAutoregressively generating disappointment, one token at "
          "a time .....\nDone! (23.36s)\n━━━━━\n \n")


def assistant_msg(rep: dict, banner: bool = False) -> dict:
    """What pi sends back for an assistant turn (reasoning_content always present for DeepSeek); banner=True replays
    it the way pi does for the first reply after a llama-swap load."""
    m = {"role": "assistant", "reasoning_content": (BANNER if banner else "") + rep["reasoning"]}
    if rep["content"]:
        m["content"] = rep["content"]
    if rep["calls"]:
        m["tool_calls"] = [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                           for c in rep["calls"]]
    return m


def log_lines(path: Path, start: int) -> tuple[list[str], int]:
    data = path.read_bytes()
    keep = re.compile(r"cache|ctx=\d+\.\.\d+:\d+ .*(prompt start|prompt done)|multimodal|tool calls|vision|shutdown|persisting")
    lines = [l for l in data[start:].decode("utf-8", "replace").splitlines() if keep.search(l)]
    return lines, len(data)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--chdir", type=Path, required=True)
    ap.add_argument("--scenario", choices=["image", "text"], required=True)
    ap.add_argument("--kv-dir", type=Path, required=True)
    ap.add_argument("--port", type=int, default=5899)
    ap.add_argument("--image", type=Path, default=HOME / "Videos/vidgen/halloween-clowns-sf/.review-bench/V1/clip-2t2.png")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--system-file", type=Path, default=REPO / "rig/film-director.md",
                    help="the system prompt (pin a copy so every run of a comparison reads the same text)")
    ap.add_argument("--banner", action="store_true", help="replay turn 2 (the first reply after the restart) with llama-swap's loading banner in front of its reasoning, as pi does")
    a = ap.parse_args()
    if subprocess.run(["pgrep", "-x", "ds4-server"], capture_output=True).returncode == 0:
        sys.exit("another ds4-server is running: unload llama-swap first (one model at a time)")
    if subprocess.run(["pgrep", "-f", "ltx-2-mlx generat[e]"], capture_output=True).returncode == 0:
        sys.exit("a render is running")
    a.kv_dir.mkdir(parents=True, exist_ok=True)
    if any(a.kv_dir.iterdir()):
        sys.exit(f"{a.kv_dir} is not empty: use a fresh KV dir per run")
    logp = a.out.with_suffix(".server.log")
    rec = {"binary": str(a.binary), "chdir": str(a.chdir), "scenario": a.scenario, "banner": a.banner, "turns": []}
    system = a.system_file.read_text()
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": TASK}]
    with logp.open("ab") as log:
        pos = logp.stat().st_size
        p = start(a, log)

        def turn(name: str, messages: list) -> dict:
            nonlocal pos
            rep = chat(a.port, messages, TOOLS, a.max_tokens)
            time.sleep(0.5)
            lines, pos = log_lines(logp, pos)
            rec["turns"].append({"turn": name, "seconds": rep["seconds"], "usage": rep["usage"], "finish": rep["finish"],
                                 "calls": [c["name"] for c in rep["calls"]], "reply_chars": len(rep["content"]),
                                 "reply": rep["content"][:2000],
                                 "reasoning_chars": len(rep["reasoning"]), "ds4_log": lines})
            print(f"--- {name}: {rep['seconds']} s, finish={rep['finish']}, calls={[c['name'] for c in rep['calls']]}")
            for l in lines:
                print("    " + l[:220])
            return rep

        r1 = turn("turn 1 (fresh)", msgs)
        stop(p)
        lines, pos = log_lines(logp, pos)
        print("--- graceful stop:\n    " + "\n    ".join(l[:220] for l in lines))
        rec["stop_log"] = lines
        p = start(a, log)
        call1 = r1["calls"][0] if r1["calls"] else {"id": "call_0", "name": "read_file"}
        msgs += [assistant_msg(r1), {"role": "tool", "tool_call_id": call1["id"], "content": BRIEF}]
        r2 = turn("turn 2 (after restart: disk restore)", msgs)
        call2 = r2["calls"][0] if r2["calls"] else {"id": "call_1", "name": "review_sheet"}
        msgs += [assistant_msg(r2, a.banner), {"role": "tool", "tool_call_id": call2["id"],
                                     "content": "Contact sheet of scene 2 (take 1 of at most 3): four frames spread over the clip."}]
        if a.scenario == "image":
            img = "data:image/png;base64," + base64.b64encode(a.image.read_bytes()).decode()
            msgs.append({"role": "user", "content": [{"type": "text", "text": "Attached image(s) from tool result:"},
                                                     {"type": "image_url", "image_url": {"url": img}}]})
        r3 = turn(f"turn 3 (the review, {a.scenario})", msgs)
        if a.scenario == "image":  # the rig's context hook replaces an answered sheet with a note
            msgs[-1] = {"role": "user", "content": "[contact sheet image: shown to you once and then removed from the context]"}
        msgs += [assistant_msg(r3), {"role": "user", "content": "Thank you. In one sentence: which single change to the line would fix it?"}]
        turn("turn 4 (text follow-up)", msgs)
        stop(p)
        lines, pos = log_lines(logp, pos)
        rec["final_stop_log"] = lines
    a.out.write_text(json.dumps(rec, indent=1))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
