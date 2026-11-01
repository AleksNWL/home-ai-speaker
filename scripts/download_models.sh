#!/usr/bin/env bash
# Download Whisper (via faster-whisper on first run) hints + Piper RU voice.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIPER_DIR="${ROOT}/models/piper"
WHISPER_DIR="${ROOT}/models/whisper"
mkdir -p "${PIPER_DIR}" "${WHISPER_DIR}"

echo "=== Piper RU voice (dmitri medium) ==="
# Voices hosted on Hugging Face rhasspy/piper-voices
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/dmitri/medium"
if [[ ! -f "${PIPER_DIR}/ru_RU-dmitri-medium.onnx" ]]; then
  curl -L "${BASE}/ru_RU-dmitri-medium.onnx" -o "${PIPER_DIR}/ru_RU-dmitri-medium.onnx"
  curl -L "${BASE}/ru_RU-dmitri-medium.onnx.json" -o "${PIPER_DIR}/ru_RU-dmitri-medium.onnx.json"
else
  echo "Piper model already present."
fi

echo
echo "=== Piper binary ==="
if ! command -v piper >/dev/null 2>&1; then
  echo "Install Piper for aarch64, e.g.:"
  echo "  # download release from https://github.com/rhasspy/piper/releases"
  echo "  # place 'piper' on PATH"
else
  piper --version || true
fi

echo
echo "=== Whisper ==="
echo "faster-whisper will download '${WHISPER_DIR}' models on first STT call."
echo "Recommended on Rock Pi 4GB: tiny or base (int8)."
echo
echo "Done."
