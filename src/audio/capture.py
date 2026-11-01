from __future__ import annotations

import queue
import threading
from typing import Iterator

import numpy as np

from .vad import EnergyVad


class AudioCapture:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: int | str | None = None,
        block_size: int = 1280,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.block_size = block_size
        self._q: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)
        self._stream = None
        self._lock = threading.Lock()

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        if status:
            pass
        try:
            self._q.put_nowait(indata.copy())
        except queue.Full:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            self._q.put_nowait(indata.copy())

    def start(self) -> None:
        import sounddevice as sd

        with self._lock:
            if self._stream is not None:
                return
            while not self._q.empty():
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=self.block_size,
                device=self.device,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> None:
        with self._lock:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

    def chunks(self) -> Iterator[np.ndarray]:
        while True:
            yield self._q.get()

    def read_utterance(
        self,
        max_seconds: float,
        vad: EnergyVad | None = None,
    ) -> np.ndarray:
        """Blocking read until max_seconds or VAD end-of-speech."""
        started = False
        frames: list[np.ndarray] = []
        max_samples = int(max_seconds * self.sample_rate)
        collected = 0
        if vad:
            vad.reset()

        # Ensure stream running
        self.start()

        while collected < max_samples:
            chunk = self._q.get()
            mono = chunk[:, 0] if chunk.ndim > 1 else chunk.reshape(-1)
            frames.append(mono.copy())
            collected += mono.shape[0]
            started = True
            if vad and started and vad.process(mono):
                break

        if not frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(frames).astype(np.float32)

    def __enter__(self) -> AudioCapture:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
