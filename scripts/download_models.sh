#!/usr/bin/env bash
# Download Piper RU voice + aarch64 binary. Whisper loads on first STT call.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIPER_DIR="${ROOT}/models/piper"
WHISPER_DIR="${ROOT}/models/whisper"
mkdir -p "${PIPER_DIR}" "${WHISPER_DIR}"

echo "=== Piper RU voice (dmitri medium) ==="
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/dmitri/medium"
if [[ ! -f "${PIPER_DIR}/ru_RU-dmitri-medium.onnx" ]]; then
  curl -L "${BASE}/ru_RU-dmitri-medium.onnx" -o "${PIPER_DIR}/ru_RU-dmitri-medium.onnx"
  curl -L "${BASE}/ru_RU-dmitri-medium.onnx.json" -o "${PIPER_DIR}/ru_RU-dmitri-medium.onnx.json"
else
  echo "Piper model already present."
fi

echo
echo "=== Piper binary (linux aarch64) ==="
if [[ -x "${PIPER_DIR}/piper" ]]; then
  echo "Found ${PIPER_DIR}/piper"
  "${PIPER_DIR}/piper" --help >/dev/null 2>&1 || true
elif command -v piper >/dev/null 2>&1; then
  piper --version || true
else
  ARCH="$(uname -m)"
  if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    TMP="$(mktemp -d)"
    # Official release asset name may change — pin a known tag
    URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz"
    echo "Downloading ${URL}"
    if curl -fL "${URL}" -o "${TMP}/piper.tgz"; then
      tar -xzf "${TMP}/piper.tgz" -C "${TMP}"
      # archive usually contains piper/piper
      BIN="$(find "${TMP}" -type f -name piper | head -n1)"
      if [[ -n "${BIN}" ]]; then
        cp -a "$(dirname "${BIN}")/." "${PIPER_DIR}/"
        chmod +x "${PIPER_DIR}/piper"
        echo "Installed to ${PIPER_DIR}/piper"
      else
        echo "WARN: piper binary not found inside archive"
      fi
    else
      echo "WARN: could not download piper binary — TTS will beep until fixed"
    fi
    rm -rf "${TMP}"
  else
    echo "WARN: unsupported arch ${ARCH} — install piper manually"
  fi
fi

echo
echo "=== Whisper ==="
echo "faster-whisper downloads into ${WHISPER_DIR} on first STT call (tiny/base)."
echo
echo "Done."
