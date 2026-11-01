#!/usr/bin/env bash
# Bootstrap on Armbian (Rock Pi 4 Plus)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

sudo apt-get update

# Core packages (libatlas removed — gone on newer Ubuntu/Armbian)
sudo apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  portaudio19-dev \
  alsa-utils sox \
  curl git

# Optional: BLAS accel + MPD (ignore if unavailable)
sudo apt-get install -y libopenblas-dev || true
sudo apt-get install -y mpd mpc || true

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
# Wake word is optional (often breaks on Python 3.14 aarch64)
pip install -r requirements-wake.txt || echo "WARN: wake word deps skipped — Enter-key fallback OK"

mkdir -p data/music data/cache logs models/piper models/whisper
if [[ ! -f config/secrets.yaml ]]; then
  cp config/secrets.example.yaml config/secrets.yaml
fi

bash scripts/download_models.sh || true

echo
echo "Python: $(python3 --version)"
echo "1) Edit config/secrets.yaml (Gemini key)"
echo "2) Audio: INPUT_DEVICE=plughw:2,0 OUTPUT_DEVICE=plughw:0,0 bash scripts/audio_smoke_test.sh"
echo "3) Text test: source .venv/bin/activate && python -m src.orchestrator --text \"привет\" -v"
echo "4) Voice: python -m src.orchestrator -v   # press Enter if no wake model"
echo "5) Optional systemd: see deploy/README.md"

