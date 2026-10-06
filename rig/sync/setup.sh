#!/bin/zsh
# setup.sh — the dialogue-sync instruments' dependencies (2026-09-27, iteration 5). Not in git (GBs); this is the recipe.
#   ~/.cache/local-video/sync-venv      Python 3.12: torch, torchaudio (MMS_FA), mediapipe 0.10.21 (1.0.1 crashes on this
#                                       Mac: "graph_service.h Check failed: service_"), demucs, parselmouth, transformers
#   ~/.cache/local-video/syncnet        joonson/syncnet_python @907c0b5 + syncnet_v2.model + S3FD sfd_face.pth (VGG, Oxford)
#   ~/.cache/local-video/face_landmarker.task   MediaPipe Face Landmarker (float16)
#   HF cache: audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim (CC BY-NC-SA 4.0), htdemucs (torch hub),
#   torchaudio MMS_FA, mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16 (for rig/voice/tts.py, in mlx-audio's venv)
#   ~/.cache/local-video/omni-venv      mlx-vlm 0.7.3 + mlx-community/Qwen3-Omni-30B-A3B-Instruct-8bit (the local judge)
set -eu
C=~/.cache/local-video; mkdir -p $C
[ -x $C/sync-venv/bin/python ] || uv venv -q -p 3.12 $C/sync-venv
VIRTUAL_ENV=$C/sync-venv uv pip install -q torch torchaudio "mediapipe==0.10.21" opencv-python-headless demucs \
  praat-parselmouth librosa scipy soundfile transformers accelerate python_speech_features
[ -d $C/syncnet/src ] || git clone -q https://github.com/joonson/syncnet_python.git $C/syncnet/src
git -C $C/syncnet/src checkout -q 907c0b579c2e2d83f0eae1b2ac9e720cde4e5623
[ -s $C/syncnet/syncnet_v2.model ] || curl -sL -o $C/syncnet/syncnet_v2.model https://www.robots.ox.ac.uk/~vgg/software/lipsync/data/syncnet_v2.model
mkdir -p $C/syncnet/src/detectors/s3fd/weights
[ -s $C/syncnet/src/detectors/s3fd/weights/sfd_face.pth ] || curl -sL -o $C/syncnet/src/detectors/s3fd/weights/sfd_face.pth https://www.robots.ox.ac.uk/~vgg/software/lipsync/data/sfd_face.pth
[ -s $C/face_landmarker.task ] || curl -sL -o $C/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
[ -x $C/omni-venv/bin/python ] || { uv venv -q -p 3.12 $C/omni-venv; VIRTUAL_ENV=$C/omni-venv uv pip install -q "mlx-vlm==0.7.3" torch torchvision librosa soundfile "huggingface_hub[cli]"; }
for m in audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16 mlx-community/Qwen3-Omni-30B-A3B-Instruct-8bit; do
  $C/omni-venv/bin/hf download -q $m >/dev/null
done
echo "sync instruments ready"
