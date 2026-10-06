#!/usr/bin/env python3
"""ds4-row-smoke.py — one llama-swap model row, served by a given ds4-server binary, answers? (2026-09-26)

Reads the row's exact command from ~/repos/local-rig/config/llama-swap.yaml, swaps in --binary and --chdir, a
spare port and a fresh KV dir, starts it standalone, sends one text request (and one image request if the row
has --vision), prints the answers, timings and ds4's cache lines, and stops it gracefully (SIGTERM, never -9).
llama-swap must have nothing loaded: one model at a time.

  ds4-row-smoke.py vision --binary ~/repos/ds4-imgcache/ds4-server --chdir ~/repos/ds4-imgcache --kv-dir DIR
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CONFIG = Path.home() / "repos/local-rig/config/llama-swap.yaml"


def row_cmd(row: str) -> list[str]:
    txt = CONFIG.read_text()
    m = re.search(rf'^  "{re.escape(row)}":\n(.*?)(?=^  "|\Z|^hooks:)', txt, re.S | re.M)
    if not m:
        sys.exit(f"no row {row} in {CONFIG}")
    c = re.search(r"cmd: \|\n((?:      .*\n)+)", m.group(1))
    return shlex.split(" ".join(l.strip() for l in c.group(1).splitlines()))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("row")
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--chdir", type=Path, required=True)
    ap.add_argument("--kv-dir", type=Path, required=True)
    ap.add_argument("--port", type=int, default=5898)
    ap.add_argument("--image", type=Path, default=Path.home() / "Videos/vidgen/halloween-clowns-sf/.review-bench/V1L/clip-2t2.png")
    ap.add_argument("--log", type=Path, required=True)
    a = ap.parse_args()
    if subprocess.run(["pgrep", "-x", "ds4-server"], capture_output=True).returncode == 0:
        sys.exit("another ds4-server is running")
    cmd = row_cmd(a.row)
    if Path(cmd[0]).name != "ds4-server":
        sys.exit(f"row {a.row} is not a ds4-server row: {cmd[0]}")
    out = [str(a.binary)]
    it = iter(cmd[1:])
    for x in it:
        v = next(it) if x in ("--chdir", "--port", "--kv-disk-dir") else None
        if x == "--chdir":
            out += ["--chdir", str(a.chdir)]
        elif x == "--port":
            out += ["--port", str(a.port)]
        elif x == "--kv-disk-dir":
            out += ["--kv-disk-dir", str(a.kv_dir)]
        else:
            out.append(x)
    a.kv_dir.mkdir(parents=True, exist_ok=True)
    print("cmd:", " ".join(out))
    with a.log.open("ab") as log:
        p = subprocess.Popen(out, stdout=log, stderr=subprocess.STDOUT)
        t0 = time.time()
        while True:
            if p.poll() is not None:
                sys.exit(f"exited {p.returncode} while starting; see {a.log}")
            try:
                models = json.load(urllib.request.urlopen(f"http://127.0.0.1:{a.port}/v1/models", timeout=2))
                break
            except Exception:
                if time.time() - t0 > 300:
                    p.send_signal(signal.SIGTERM)
                    sys.exit("not up in 300 s")
                time.sleep(1)
        name = models["data"][0]["id"]
        print(f"up in {time.time() - t0:.1f} s, model {name}")
        asks = [("text", "What is 17 times 23? Answer with the number only.")]
        if "--vision" in out:
            img = "data:image/png;base64," + base64.b64encode(a.image.read_bytes()).decode()
            asks.append(("image", [{"type": "text", "text": "Name the bridge in these frames and its colour, in one short sentence."},
                                   {"type": "image_url", "image_url": {"url": img}}]))
        for kind, content in asks:
            body = {"model": name, "messages": [{"role": "user", "content": content}], "max_tokens": 1500,
                    "reasoning_effort": "low", "temperature": 0}
            t1 = time.time()
            j = json.load(urllib.request.urlopen(urllib.request.Request(
                f"http://127.0.0.1:{a.port}/v1/chat/completions", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"}), timeout=900))
            msg = j["choices"][0]["message"]
            print(f"{kind}: {time.time() - t1:.1f} s, finish={j['choices'][0].get('finish_reason')}, answer={(msg.get('content') or '').strip()[:200]!r}")
        p.send_signal(signal.SIGTERM)
        try:
            p.wait(timeout=240)
        except subprocess.TimeoutExpired:
            print("WARNING: still running 240 s after SIGTERM; not killed")
    lines = [l for l in a.log.read_text(errors="replace").splitlines() if re.search(r"cache|prompt done|listening|error|fail", l, re.I)]
    print("\n".join(lines[-12:]))


if __name__ == "__main__":
    main()
