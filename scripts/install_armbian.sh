#!/usr/bin/env bash
# Bootstrap on Armbian (Rock Pi 4 Plus)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  portaudio19-dev libatlas-base-dev \
  alsa-utils sox \
  mpd mpc \
  curl git

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt

mkdir -p data/music data/cache logs models/piper models/whisper
cp -n config/secrets.example.yaml config/secrets.yaml || true

bash scripts/download_models.sh || true

echo
echo "1) Edit config/secrets.yaml (Gemini + optional HA token)"
echo "2) Run audio smoke: bash scripts/audio_smoke_test.sh"
echo "3) Run: source .venv/bin/activate && python -m src.orchestrator -v"
echo "4) Install systemd (optional):"
echo "   sudo cp systemd/home-ai-speaker.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload && sudo systemctl enable --now home-ai-speaker"
