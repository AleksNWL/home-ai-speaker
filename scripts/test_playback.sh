#!/usr/bin/env bash
# Find which ALSA device actually plays sound (Crown / HDMI / FiFine).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

echo "=== Playback devices ==="
aplay -l || true
echo

# Generate a short beep wav via sox or python
BEEP=/tmp/has-beep.wav
if command -v sox >/dev/null 2>&1; then
  sox -n -r 22050 -c 1 "${BEEP}" synth 0.6 sine 880 vol 0.3
else
  python3 - <<'PY'
import math, struct, wave
path = "/tmp/has-beep.wav"
rate, dur, freq = 22050, 0.6, 880.0
n = int(rate * dur)
with wave.open(path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(rate)
    for i in range(n):
        v = int(0.3 * 32767 * math.sin(2 * math.pi * freq * i / rate))
        wf.writeframes(struct.pack("<h", v))
print("wrote", path)
PY
fi

echo "=== Test beep on each card ==="
# card 0 Analog, 1 hdmi, 2 fifine — try all
for DEV in plughw:0,0 plughw:1,0 plughw:2,0 default; do
  echo
  echo ">>> Playing on ${DEV} (слушай 1 сек)..."
  if aplay -D "${DEV}" -q "${BEEP}" 2>/tmp/aplay-err.txt; then
    echo "OK command succeeded for ${DEV}"
  else
    echo "FAIL ${DEV}: $(cat /tmp/aplay-err.txt)"
  fi
  sleep 0.3
done

echo
echo "=== Piper TTS sample (if models present) ==="
PIPER="${ROOT}/models/piper/piper"
MODEL="${ROOT}/models/piper/ru_RU-dmitri-medium.onnx"
OUT=/tmp/has-tts.wav
if [[ -x "${PIPER}" && -f "${MODEL}" ]]; then
  echo "Синтез..."
  echo "Проверка озвучки колонки" | "${PIPER}" --model "${MODEL}" --output_file "${OUT}"
  for DEV in plughw:0,0 plughw:2,0 plughw:1,0; do
    echo ">>> Piper on ${DEV}..."
    aplay -D "${DEV}" -q "${OUT}" 2>/tmp/aplay-err.txt && echo "OK ${DEV}" || echo "FAIL ${DEV}: $(cat /tmp/aplay-err.txt)"
    sleep 0.3
  done
else
  echo "Piper/model missing — skip TTS part"
fi

echo
echo "Напиши, на каком DEV был слышен звук — пропишем alsa_output в config/default.yaml"
