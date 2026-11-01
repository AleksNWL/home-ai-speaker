#!/usr/bin/env bash
# Stage 0 — audio smoke test for Rock Pi / Armbian
# Usage: bash scripts/audio_smoke_test.sh

set -euo pipefail

DURATION="${DURATION:-3}"
RATE_CAP="${RATE_CAP:-16000}"
RATE_PLAY="${RATE_PLAY:-48000}"
TMPDIR="${TMPDIR:-/tmp}"
REC_FILE="${TMPDIR}/home-ai-speaker-smoke.wav"

echo "=== home-ai-speaker audio smoke test ==="
echo "Capture ${DURATION}s @ ${RATE_CAP} Hz → play back"
echo

if command -v arecord >/dev/null 2>&1; then
  echo "[1/4] Recording devices (arecord -l):"
  arecord -l || true
  echo
  echo "[2/4] Playback devices (aplay -l):"
  aplay -l || true
  echo
  echo "[3/4] Recording ${DURATION}s to ${REC_FILE} ..."
  arecord -f S16_LE -r "${RATE_CAP}" -c 1 -d "${DURATION}" "${REC_FILE}"
  echo "[4/4] Playing back ..."
  aplay "${REC_FILE}"
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
echo "Next: set audio.input_device / audio.output_device in config/default.yaml if defaults are wrong."
echo "Tip: python -c \"import sounddevice as sd; print(sd.query_devices())\""
