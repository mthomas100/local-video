#!/bin/zsh
# setup.sh — idempotent installer for the local video rig (2026-09-22). Safe to re-run;
# every step checks before it acts. Run it after a fresh clone, after `git pull` in the
# engine, or when a download was interrupted. What it sets up is described in README.md.
set -euo pipefail
here=${0:a:h}
say() { print -P "%F{cyan}==>%f $*"; }

say "1/5 tools (uv, ffmpeg, hf CLI)"
for t in uv ffmpeg hf; do command -v $t >/dev/null || { echo "missing $t (brew install uv ffmpeg; pip3 install -U huggingface_hub)"; exit 1; }; done

say "2/5 engine: ~/repos/ltx-2-mlx (dgrauet/ltx-2-mlx, MIT, pure MLX)"
if [ ! -d ~/repos/ltx-2-mlx/.git ]; then git clone -q https://github.com/dgrauet/ltx-2-mlx.git ~/repos/ltx-2-mlx; fi
(cd ~/repos/ltx-2-mlx && uv sync --all-extras -q && .venv/bin/ltx-2-mlx --help >/dev/null) && say "    engine ok ($(git -C ~/repos/ltx-2-mlx rev-parse --short HEAD))"

say "3/5 weights in ~/models (resumable; runs in the background, see logs/)"
mkdir -p ~/models ~/Videos/vidgen $here/logs
for repo in dgrauet/ltx-2.5-mlx-q8 dgrauet/ltx-2.3-mlx-q8; do
  name=${repo##*/}
  if [ -f ~/models/$name/transformer-distilled.safetensors ] && ! ls ~/models/$name/*.incomplete >/dev/null 2>&1; then
    say "    $name complete ($(du -sh ~/models/$name | cut -f1))"
  elif pgrep -f "fetch-weights $repo" >/dev/null; then
    say "    $name download already running"
  else
    nohup $here/bin/fetch-weights $repo >/dev/null 2>&1 &
    say "    $name download started (gated repo? accept the licence at https://huggingface.co/$repo)"
  fi
done

say "4/5 command, skills, pi extension and agent (every link is in bin/apparatus; see APPARATUS.md)"
$here/bin/apparatus link | sed 's/^/    /'
[ -x ~/repos/imagegen/.venv/bin/mflux-generate-qwen-2.1 ] || say "    image models for [still]/[ref]: run rig/keyframe/setup-imagegen.sh (about 50 GB of weights)"

say "5/5 GUI apps (optional; installed from their vendors' direct downloads)"
[ -d "/Applications/Draw Things.app" ] && say "    Draw Things $(defaults read '/Applications/Draw Things.app/Contents/Info.plist' CFBundleShortVersionString) present" || say "    Draw Things missing: https://drawthings.ai/downloads/"
[ -d "/Applications/LTX Desktop.app" ] && say "    LTX Desktop $(defaults read '/Applications/LTX Desktop.app/Contents/Info.plist' CFBundleShortVersionString) present" || say "    LTX Desktop missing: https://github.com/Lightricks/LTX-Desktop/releases"
say "done. try: vidgen --dry-run \"a red fox in snow\""
