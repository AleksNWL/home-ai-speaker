from __future__ import annotations

import numpy as np


class EnergyVad:
    """Simple RMS energy VAD for end-of-utterance detection."""

    def __init__(self, threshold: float = 0.012, silence_ms: int = 900, sample_rate: int = 16000) -> None:
        self.threshold = threshold
        self.silence_ms = silence_ms
        self.sample_rate = sample_rate
        self._silent_samples = 0
        self._heard_speech = False

    def reset(self) -> None:
        self._silent_samples = 0
        self._heard_speech = False

    def process(self, chunk: np.ndarray) -> bool:
        """Return True when utterance should end (speech heard, then silence)."""
        if chunk.size == 0:
            return False
        rms = float(np.sqrt(np.mean(np.square(chunk.astype(np.float32)))))
        if rms >= self.threshold:
            self._heard_speech = True
            self._silent_samples = 0
            return False
        if not self._heard_speech:
            return False
        self._silent_samples += chunk.shape[0]
        silence_needed = int(self.sample_rate * (self.silence_ms / 1000.0))
        return self._silent_samples >= silence_needed
