# Deploy on Rock Pi (Armbian)

1. Copy project to `/opt/home-ai-speaker`
2. `bash scripts/install_armbian.sh`
3. Fill `config/secrets.yaml`
4. Audio smoke: `bash scripts/audio_smoke_test.sh`
5. Optional MPD: use `mpd.conf.example`
6. `sudo cp systemd/home-ai-speaker.service /etc/systemd/system/`  
   Edit `User=` if needed, then `systemctl enable --now home-ai-speaker`
7. With HDMI screen: enable `home-ai-display-kiosk.service`
