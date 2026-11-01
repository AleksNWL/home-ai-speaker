from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class WhisperSTT:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: str | Path | None = None,
        language: str = "ru",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = str(download_root) if download_root else None
        self.language = language
        self._model = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        logger.info("Loading Whisper model=%s compute=%s", self.model_size, self.compute_type)
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            download_root=self.download_root,
        )

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if audio.size == 0:
            return ""
        self._ensure_model()
        assert self._model is not None
        # faster-whisper expects float32 mono 16k
        if sample_rate != 16000:
            # naive resample
            duration = audio.shape[0] / float(sample_rate)
            target = int(duration * 16000)
            x_old = np.linspace(0, 1, num=audio.shape[0], endpoint=False)
            x_new = np.linspace(0, 1, num=target, endpoint=False)
            audio = np.interp(x_new, x_old, audio).astype(np.float32)
        audio = audio.astype(np.float32)
        segments, _info = self._model.transcribe(
            audio,
            language=self.language,
            vad_filter=True,
            beam_size=1,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.info("STT: %s", text)
        return text
