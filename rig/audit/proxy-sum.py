#!/usr/bin/env python3
"""proxy-sum.py <start HH:MM:SS> <end HH:MM:SS> [log] — llama-swap proxy log for a day (env DAY, default "Sep 26") in a window: chat requests
(count, total and largest duration), model starts and unloads. Metadata only."""
import re, sys, os
start, end = sys.argv[1], sys.argv[2]
DAY = os.environ.get("DAY", "Sep 26") + " "
log = sys.argv[3] if len(sys.argv) > 3 else os.path.expanduser("~/.ds4/llama-swap.log")
def secs(d):
    t = 0.0
    for v, u in re.findall(r"([0-9.]+)(h|ms|µs|m|s)", d):
        t += float(v) * {"h": 3600, "m": 60, "s": 1, "ms": 1e-3, "µs": 1e-6}[u]
    return t
n = 0; tot = 0.0; big = []
for line in open(log, errors="replace"):
    if not line.startswith(DAY): continue
    hms = line[7:15]
    if not (start <= hms <= end): continue
    m = re.search(r'"POST /v1/chat/completions[^"]*" (\d+) \d+ "[^"]*" ([0-9hms.µ]+)$', line.strip())
    if m:
        d = secs(m.group(2)); n += 1; tot += d; big.append((d, hms, m.group(1)))
    elif "starting" in line or "unload" in line.lower() or "stopp" in line.lower() or "ready" in line.lower():
        print("  ", line.strip()[:160])
print(f"chat requests {n}, total {tot/60:.1f} min; largest: " + ", ".join(f"{h} {d:.0f}s" for d, h, _ in sorted(big, reverse=True)[:6]))
bad = [(h, c) for d, h, c in big if c != "200"]
print("non-200:", bad or "none")
