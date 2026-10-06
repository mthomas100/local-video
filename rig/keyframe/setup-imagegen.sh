#!/bin/zsh
# setup-imagegen.sh — rebuild the image-model side of the rig (2026-09-27): the venv ~/repos/imagegen/.venv with
# mflux, and the weights bin/still uses. The venv and weights live outside git (tens of GB); this script is their
# version-controlled recipe. Offline use afterwards: bin/still sets HF_HUB_OFFLINE=1.
#   Qwen-Image-2.1 (33 GB, Qwen Research License, non-commercial): text-to-image stills, chosen 2026-09-26 (IMAGE-MODEL.md)
#   Z-Image Turbo 4-bit (6 GB): the fallback
#   FLUX.2 klein 4B (15 GB, Apache-2.0): multi-reference EDIT, added 2026-09-27 for one face per character and for
#     placing characters into a reference photo of a place ([ref=...], bin/still --ref)
set -eu
MFLUX_VERSION=0.20.0
mkdir -p ~/repos/imagegen/logs
cd ~/repos/imagegen
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python "mflux==$MFLUX_VERSION"
for repo in Qwen/Qwen-Image-2.1 filipstrand/Z-Image-Turbo-mflux-4bit black-forest-labs/FLUX.2-klein-4B; do
  .venv/bin/hf download $repo > logs/download-${repo:t}.log 2>&1 || { echo "download of $repo failed; see logs/"; exit 1; }
done
echo "imagegen ready: mflux $MFLUX_VERSION, $(du -sh ~/.cache/huggingface/hub | cut -f1) of weights"
