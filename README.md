# home-ai-speaker

Гибридная умная колонка для **Rock Pi 4 Plus** (Armbian): wake word + STT/TTS локально, **Gemini** для диалога, **Home Assistant** и **MPD** для дома и музыки.

## Архитектура

```
Mic → Wake Word → STT → Orchestrator → Gemini / local skills → TTS → Speakers
                                      ↘ HA / MPD / Weather / Timers
Display kiosk ← HTTP status :8787
```

## Быстрый старт (на Rock Pi)

```bash
git clone <repo> /opt/home-ai-speaker
cd /opt/home-ai-speaker
bash scripts/install_armbian.sh
nano config/secrets.yaml   # Gemini API key, optional HA token

# Stage 0 — audio
bash scripts/audio_smoke_test.sh
# or: source .venv/bin/activate && python scripts/audio_smoke_test.py

# Run assistant
source .venv/bin/activate
python -m src.orchestrator -v
```

Без микрофона (проверка LLM/навыков):

```bash
python -m src.orchestrator --text "какая погода" -v
```

Если openWakeWord не установился (часто на **Python 3.14** / aarch64 из‑за `tflite-runtime`) — режим fallback: нажми **Enter** в терминале, чтобы имитировать wake word. Позже можно поставить Python 3.11/3.12 и `pip install -r requirements-wake.txt`.

## Конфиг

| Файл | Назначение |
|------|------------|
| `config/default.yaml` | Аудио, модели, skills, порт UI |
| `config/secrets.yaml` | API keys (из `secrets.example.yaml`) |

После smoke-теста пропиши `audio.input_device` / `audio.output_device`, если дефолт неверный:

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

## Systemd

```bash
sudo mkdir -p /opt/home-ai-speaker
sudo rsync -a ./ /opt/home-ai-speaker/
# fix User= in unit if not `rock`
sudo cp systemd/home-ai-speaker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now home-ai-speaker
```

Экран (kiosk): `systemd/home-ai-display-kiosk.service` → `http://127.0.0.1:8787/`

## Музыка (MPD)

```bash
sudo cp deploy/mpd.conf.example /etc/mpd.conf   # правь пути
sudo systemctl enable --now mpd
# положи файлы в data/music и: mpc update
```

## Корпус

Черновик OpenSCAD и заметки: [`case/README.md`](case/README.md).

## Этапы

0. Аудио smoke  
1. Wake → STT → TTS  
2. Gemini + skills  
3. Home Assistant  
4. MPD  
5. systemd + статус  
6. Экран + корпус  

## Требования к железу

Rock Pi 4 Plus 4GB: Whisper `tiny`/`base` + Piper + Gemini. Полноценную локальную LLM на этой плате не планируем.
