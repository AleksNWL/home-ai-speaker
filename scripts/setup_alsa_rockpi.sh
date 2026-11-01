#!/usr/bin/env bash
# ES8316 on Rock Pi: unmute path to 3.5mm jack (Crown speakers).
set -euo pipefail

echo "=== Configure card 0 (Analog / ES8316) ==="
amixer -c 0 sset 'Headphone Mixer' 11
amixer -c 0 sset DAC 192
amixer -c 0 sset Headphone 3
amixer -c 0 sset 'Left Headphone Mixer Left DAC' on 2>/dev/null || true
amixer -c 0 sset 'Right Headphone Mixer Right DAC' on 2>/dev/null || true

# Persist if alsactl available
if command -v alsactl >/dev/null 2>&1; then
  alsactl store 0 || sudo alsactl store 0 || true
  echo "alsactl store done"
fi

echo
echo "Test: aplay -D plughw:0,0 /tmp/has-beep.wav"
echo "Config: audio.alsa_output: \"plughw:0,0\" in config/default.yaml"
