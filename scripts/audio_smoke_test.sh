#!/usr/bin/env bash
# Stage 0 — audio smoke test for Rock Pi / Armbian
# Usage:
#   bash scripts/audio_smoke_test.sh
#   INPUT_DEVICE=plughw:2,0 OUTPUT_DEVICE=plughw:0,0 bash scripts/audio_smoke_test.sh

set -euo pipefail

DURATION="${DURATION:-3}"
RATE_CAP="${RATE_CAP:-16000}"
TMPDIR="${TMPDIR:-/tmp}"
REC_FILE="${TMPDIR}/home-ai-speaker-smoke.wav"
# FiFine AM8 is often card 2 on Rock Pi — override if needed
INPUT_DEVICE="${INPUT_DEVICE:-plughw:2,0}"
OUTPUT_DEVICE="${OUTPUT_DEVICE:-plughw:0,0}"

echo "=== home-ai-speaker audio smoke test ==="
echo "Capture ${DURATION}s @ ${RATE_CAP} Hz"
echo "Input:  ${INPUT_DEVICE}"
echo "Output: ${OUTPUT_DEVICE}"
echo

if command -v arecord >/dev/null 2>&1; then
  echo "[1/4] Recording devices (arecord -l):"
  arecord -l || true
  echo
  echo "[2/4] Playback devices (aplay -l):"
  aplay -l || true
  echo
  echo "[3/4] Recording ${DURATION}s to ${REC_FILE} ..."
  arecord -D "${INPUT_DEVICE}" -f S16_LE -r "${RATE_CAP}" -c 1 -d "${DURATION}" "${REC_FILE}"
  echo "[4/4] Playing back on ${OUTPUT_DEVICE} ..."
  aplay -D "${OUTPUT_DEVICE}" "${REC_FILE}"
  echo
  echo "OK: ALSA record+play completed."
else
  echo "arecord/aplay not found. Install: sudo apt install alsa-utils"
  exit 1
fi

echo
echo "PipeWire / Pulse status (if present):"
if command -v wpctl >/dev/null 2>&1; then
  wpctl status || true
elif command -v pactl >/dev/null 2>&1; then
  pactl info || true
  pactl list short sources || true
  pactl list short sinks || true
else
  echo "(no wpctl/pactl — pure ALSA is fine for the speaker)"
fi

echo
echo "If mic/speakers wrong, retry with:"
echo "  INPUT_DEVICE=plughw:2,0 OUTPUT_DEVICE=plughw:0,0 bash scripts/audio_smoke_test.sh"
echo "Then set devices in config/default.yaml after: python -c \"import sounddevice as sd; print(sd.query_devices())\""
