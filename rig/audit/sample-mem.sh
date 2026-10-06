#!/bin/bash
# sample-mem.sh <out.csv> [max-seconds] — every 5 s, one CSV row: the phase (render: an LTX process exists;
# still: the image model draws a first frame; llm: llama-swap has a model loaded; idle), the scene being rendered, LTX RSS, wired/active/compressed/free
# memory and the GPU's device and renderer utilization and memory from ioreg (no sudo) (2026-09-24).
# Start it in the background (nohup ... &) at the start of a film and kill it at the end. Appends if the
# file exists. Read-only; safe during a render.
OUT=$1; MAX=${2:-14400}; end=$(( $(date +%s) + MAX ))
[ -f "$OUT" ] || echo "ts,phase,scene,ltx_rss_gb,wired_gb,active_gb,compressed_gb,free_gb,gpu_dev_pct,gpu_rend_pct,gpu_alloc_gb,gpu_inuse_gb" > "$OUT"
PS=$(vm_stat | awk '/page size/{print $8}')
while [ "$(date +%s)" -lt "$end" ]; do
  ltx=$(ps -axo rss,command | grep "ltx-2-mlx generat[e]" | head -1)
  if [ -n "$ltx" ]; then
    phase=render; rss=$(echo "$ltx" | awk '{printf "%.1f", $1/1048576}')
    scene=$(echo "$ltx" | grep -oE 'scene-[0-9]+\.mp4' | head -1 | sed -E 's/scene-([0-9]+).*/\1/')
  else
    rss=0; scene=""
    # still (2026-09-27): bin/still's image model (mflux) on the GPU; on 2026-09-26 its 21 min were labelled idle
    img=$(ps -axo rss,command | grep -E "mflux-generate[-a-z0-9.]*" | grep -v grep | head -1)
    if [ -n "$img" ]; then phase=still; rss=$(echo "$img" | awk '{printf "%.1f", $1/1048576}')
    elif curl -s -m 2 127.0.0.1:8090/running | grep -q '"model"'; then phase=llm; else phase=idle; fi
  fi
  mem=$(vm_stat | awk -v ps=$PS '/wired down/{w=$4} /Pages active/{a=$3} /occupied by compressor/{c=$5} /Pages free/{f=$3} END{gsub("\\.","",w);gsub("\\.","",a);gsub("\\.","",c);gsub("\\.","",f); printf "%.1f,%.1f,%.1f,%.1f", w*ps/1e9, a*ps/1e9, c*ps/1e9, f*ps/1e9}')
  gpu=$(ioreg -r -d 1 -w 0 -c IOAccelerator | awk '
    function val(key,   s) { if (match($0, "\"" key "\"=[0-9]+")) { s = substr($0, RSTART, RLENGTH); sub(/.*=/, "", s); return s } return "" }
    { d = d == "" ? val("Device Utilization %") : d; r = r == "" ? val("Renderer Utilization %") : r
      a = a == "" ? val("Alloc system memory") : a; u = u == "" ? val("In use system memory") : u }
    END { printf "%s,%s,%.1f,%.1f", d, r, a/1e9, u/1e9 }')
  echo "$(date +%H:%M:%S),$phase,$scene,$rss,$mem,$gpu" >> "$OUT"
  sleep 5
done
