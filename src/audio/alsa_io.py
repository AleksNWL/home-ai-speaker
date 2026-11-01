from __future__ import annotations

import logging
import queue
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from typing import Iterator

import numpy as np

from .vad import EnergyVad

logger = logging.getLogger(__name__)


class AlsaCapture:
    """Capture via `arecord` — works on pure ALSA (no PulseAudio/PortAudio)."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: str | None = "plughw:2,0",
        block_size: int = 1280,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device or "default"
        self.block_size = block_size
        self._q: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def _reader(self) -> None:
        assert self._proc and self._proc.stdout
        bytes_per_block = self.block_size * self.channels * 2  # S16_LE
        while not self._stop.is_set():
            raw = self._proc.stdout.read(bytes_per_block)
            if not raw:
                break
            pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if self.channels > 1:
                pcm = pcm.reshape(-1, self.channels)[:, 0]
            try:
                self._q.put_nowait(pcm.copy())
            except queue.Full:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    pass
                self._q.put_nowait(pcm.copy())

    def start(self) -> None:
        with self._lock:
            if self._proc is not None:
                return
            while not self._q.empty():
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
            self._stop.clear()
            cmd = [
                "arecord",
                "-D",
                str(self.device),
                "-f",
                "S16_LE",
                "-r",
                str(self.sample_rate),
                "-c",
                str(self.channels),
                "-t",
                "raw",
                "-q",
                "-",
            ]
            logger.info("ALSA capture: %s", " ".join(cmd))
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._thread = threading.Thread(target=self._reader, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop.set()
            if self._proc is not None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                self._proc = None
            if self._thread is not None:
                self._thread.join(timeout=1.5)
                self._thread = None

    def chunks(self) -> Iterator[np.ndarray]:
        while True:
            yield self._q.get()

    def read_utterance(
        self,
        max_seconds: float,
        vad: EnergyVad | None = None,
    ) -> np.ndarray:
        frames: list[np.ndarray] = []
        max_samples = int(max_seconds * self.sample_rate)
        collected = 0
        if vad:
            vad.reset()
        self.start()
        while collected < max_samples:
            chunk = self._q.get()
            mono = chunk.reshape(-1)
            frames.append(mono.copy())
            collected += mono.shape[0]
            if vad and vad.process(mono):
                break
        if not frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(frames).astype(np.float32)

    def __enter__(self) -> AlsaCapture:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


class AlsaPlayback:
    """Playback via `aplay`."""

    def __init__(
        self,
        sample_rate: int = 22050,
        device: str | None = "plughw:0,0",
    ) -> None:
        self.sample_rate = sample_rate
        self.device = device or "default"
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None

    @staticmethod
    def _ensure_rockpi_jack_levels() -> None:
        """ES8316 often boots with Headphone Mixer at 0 — bump before each play."""
        cmds = [
            ["amixer", "-c", "0", "-q", "sset", "Headphone Mixer", "11"],
            ["amixer", "-c", "0", "-q", "sset", "DAC", "192"],
            ["amixer", "-c", "0", "-q", "sset", "Headphone", "3"],
        ]
        for cmd in cmds:
            try:
                subprocess.run(cmd, check=False, capture_output=True)
            except Exception:
                pass

    def play(self, audio: np.ndarray, sample_rate: int | None = None) -> None:
        rate = sample_rate or self.sample_rate
        if audio.size == 0:
            logger.warning("ALSA play: empty audio buffer")
            return
        data = np.asarray(audio, dtype=np.float32).reshape(-1)
        peak = float(np.max(np.abs(data))) if data.size else 0.0
        if peak > 1.0:
            data = data / peak
        if peak < 0.001:
            logger.warning("ALSA play: near-silent buffer (peak=%.6f)", peak)
        pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)

        # Crown on Rock Pi 3.5mm (card 0)
        if str(self.device).startswith("plughw:0") or str(self.device).startswith("hw:0"):
            self._ensure_rockpi_jack_levels()

        with self._lock:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = Path(tmp.name)
            try:
                with wave.open(str(path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(rate)
                    wf.writeframes(pcm.tobytes())
                duration = pcm.shape[0] / float(rate)
                cmd = ["aplay", "-D", str(self.device), str(path)]
                print(f"🔊 play {duration:.1f}s → {self.device}", flush=True)
                logger.info("ALSA play: %s (%.1fs, peak=%.3f)", " ".join(cmd), duration, peak)
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                _stdout, stderr = self._proc.communicate()
                code = self._proc.returncode
                if code != 0:
                    err = (stderr or b"").decode("utf-8", errors="ignore").strip()
                    logger.error("aplay failed code=%s: %s", code, err)
                    print(f"aplay ERROR {code}: {err}", flush=True)
            finally:
                self._proc = None
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            self._proc = None
