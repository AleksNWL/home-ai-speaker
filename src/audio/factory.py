from __future__ import annotations

import logging
from typing import Any

from .vad import EnergyVad

logger = logging.getLogger(__name__)


def create_capture(audio_cfg: dict[str, Any]):
    backend = (audio_cfg.get("backend") or "alsa").lower()
    rate = int(audio_cfg.get("sample_rate_capture", 16000))
    channels = int(audio_cfg.get("channels", 1))

    if backend == "alsa":
        from .alsa_io import AlsaCapture

        device = audio_cfg.get("alsa_input") or audio_cfg.get("input_device") or "plughw:2,0"
        logger.info("Audio capture backend=alsa device=%s", device)
        return AlsaCapture(sample_rate=rate, channels=channels, device=str(device))

    from .capture import AudioCapture

    logger.info("Audio capture backend=sounddevice")
    return AudioCapture(
        sample_rate=rate,
        channels=channels,
        device=audio_cfg.get("input_device"),
    )


def create_playback(audio_cfg: dict[str, Any]):
    backend = (audio_cfg.get("backend") or "alsa").lower()
    rate = int(audio_cfg.get("sample_rate_playback", 22050))

    if backend == "alsa":
        from .alsa_io import AlsaPlayback

        device = audio_cfg.get("alsa_output") or audio_cfg.get("output_device") or "plughw:0,0"
        logger.info("Audio playback backend=alsa device=%s", device)
        return AlsaPlayback(sample_rate=rate, device=str(device))

    from .playback import AudioPlayback

    logger.info("Audio playback backend=sounddevice")
    return AudioPlayback(sample_rate=rate, device=audio_cfg.get("output_device"))


__all__ = ["EnergyVad", "create_capture", "create_playback"]
