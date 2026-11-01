"""Audio capture / playback helpers."""

from __future__ import annotations

from .factory import create_capture, create_playback
from .vad import EnergyVad

__all__ = ["EnergyVad", "create_capture", "create_playback", "AudioCapture", "AudioPlayback"]


def __getattr__(name: str):
    if name == "AudioCapture":
        from .capture import AudioCapture as _AudioCapture

        return _AudioCapture
    if name == "AudioPlayback":
        from .playback import AudioPlayback as _AudioPlayback

        return _AudioPlayback
    raise AttributeError(name)
