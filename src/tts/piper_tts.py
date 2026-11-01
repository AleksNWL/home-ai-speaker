from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class PiperTTS:
    """TTS via Piper CLI. Falls back to a short beep if Piper is missing."""

    def __init__(
        self,
        model_path: str | Path,
        config_path: str | Path | None = None,
        piper_binary: str = "piper",
        speak_rate: float = 1.0,
    ) -> None:
        self.model_path = Path(model_path)
        self.config_path = Path(config_path) if config_path else None
        self.speak_rate = speak_rate
        bin_path = Path(piper_binary)
        if bin_path.exists() and bin_path.is_file():
            self.piper_binary = str(bin_path)
        else:
            found = shutil.which(piper_binary)
            self.piper_binary = found or piper_binary
        self._available = Path(self.piper_binary).exists() and self.model_path.exists()
        if not self._available:
            logger.warning(
                "Piper not ready (binary=%s model=%s) — using beep fallback",
                self.piper_binary,
                self.model_path,
            )


    @property
    def available(self) -> bool:
        return self._available

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        text = (text or "").strip()
        if not text:
            return np.zeros(0, dtype=np.float32), 22050
        if not self._available:
            return self._beep(), 22050

        with tempfile.TemporaryDirectory() as tmp:
            out_wav = Path(tmp) / "out.wav"
            cmd = [
                self.piper_binary,
                "--model",
                str(self.model_path),
                "--output_file",
                str(out_wav),
            ]
            if self.config_path and self.config_path.exists():
                cmd.extend(["--config", str(self.config_path)])
            if self.speak_rate and self.speak_rate != 1.0:
                cmd.extend(["--length_scale", str(1.0 / self.speak_rate)])
            logger.info("Piper TTS: %s", text[:80])
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                check=False,
            )
            if proc.returncode != 0 or not out_wav.exists():
                logger.error("Piper failed: %s", proc.stderr.decode("utf-8", errors="ignore"))
                return self._beep(), 22050
            return self._read_wav(out_wav)

    @staticmethod
    def _read_wav(path: Path) -> tuple[np.ndarray, int]:
        with wave.open(str(path), "rb") as wf:
            rate = wf.getframerate()
            nch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(wf.getnframes())
        if sw == 2:
            pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            raise ValueError(f"Unsupported sample width: {sw}")
        if nch > 1:
            pcm = pcm.reshape(-1, nch).mean(axis=1)
        return pcm, rate

    @staticmethod
    def _beep(freq: float = 880.0, duration: float = 0.25, rate: int = 22050) -> np.ndarray:
        t = np.linspace(0, duration, int(rate * duration), endpoint=False)
        wave_data = 0.2 * np.sin(2 * np.pi * freq * t)
        # simple envelope
        env = np.linspace(0, 1, int(rate * 0.02))
        wave_data[: env.size] *= env
        wave_data[-env.size :] *= env[::-1]
        return wave_data.astype(np.float32)

    @staticmethod
    def write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())
