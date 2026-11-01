from __future__ import annotations

import threading

import numpy as np


class AudioPlayback:
    def __init__(
        self,
        sample_rate: int = 22050,
        device: int | str | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.device = device
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def play(self, audio: np.ndarray, sample_rate: int | None = None) -> None:
        import sounddevice as sd

        rate = sample_rate or self.sample_rate
        if audio.size == 0:
            return
        data = np.asarray(audio, dtype=np.float32)
        if data.ndim > 1:
            data = data.reshape(-1)
        peak = float(np.max(np.abs(data))) if data.size else 0.0
        if peak > 1.0:
            data = data / peak
        self._stop.clear()
        with self._lock:
            sd.play(data, samplerate=rate, device=self.device)
            # Poll so stop() can interrupt
            while sd.get_stream().active if sd.get_stream() else False:
                if self._stop.wait(0.05):
                    sd.stop()
                    break
            try:
                sd.wait()
            except Exception:
                pass

    def play_wav_bytes(self, wav_bytes: bytes) -> None:
        import io
        import wave

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            rate = wf.getframerate()
            nch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(wf.getnframes())
        if sw == 2:
            pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            raise ValueError(f"Unsupported sample width: {sw}")
        if nch > 1:
            pcm = pcm.reshape(-1, nch)[:, 0]
        self.play(pcm, sample_rate=rate)

    def stop(self) -> None:
        import sounddevice as sd

        self._stop.set()
        sd.stop()
