"""Audio capture / playback helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .capture import AudioCapture
    from .playback import AudioPlayback
    from .vad import EnergyVad

__all__ = ["AudioCapture", "AudioPlayback", "EnergyVad"]


def __getattr__(name: str):
    if name == "AudioCapture":
        from .capture import AudioCapture as _AudioCapture

        return _AudioCapture
    if name == "AudioPlayback":
        from .playback import AudioPlayback as _AudioPlayback

        return _AudioPlayback
    if name == "EnergyVad":
        from .vad import EnergyVad as _EnergyVad

        return _EnergyVad
    raise AttributeError(name)
